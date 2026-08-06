"""Seed a realistic Arabic dataset for perf / RTL / bidi / search testing.

Creates a workspace → database → table filled with `--rows` employees:

    الاسم (Name)              text       — Arabic full names (sorting / bidi)
    رقم الإقامة (Iqama No.)   text       — 10-digit ids (LTR digits inside RTL rows)
    القسم (Department)        text       — Arabic department names
    تاريخ التعيين (Hire date) date (ISO) — Gregorian, the canonical stored value
    التاريخ الهجري (Hijri)    text       — Hijri display string (Phase 2 → hijri_date)
    ملاحظات (Notes)           long_text  — mixed Arabic + Latin codes/numbers

The first dozen rows are curated edge cases used by docs/AUDIT.md (ta-marbuta,
hamza/alef, madda, tatweel) so the search-normalization tests have known targets.

Usage (inside the backend container):

    ./jadawel seed_arabic_data --rows 50000
    ./jadawel seed_arabic_data --rows 1000 --user-email admin@example.com

Idempotency: each run creates a *new* table and prints its id; nothing existing is
mutated. Use a small --rows first to smoke-test, then 50000 for the perf baseline.
"""

import random
import time
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from jadawel.contrib.database.application_types import DatabaseApplicationType
from jadawel.contrib.database.search.handler import SearchHandler
from jadawel.contrib.database.table.handler import TableHandler
from jadawel.core.handler import CoreHandler

User = get_user_model()

# --- Arabic data pools ------------------------------------------------------

MALE_FIRST = [
    "محمد",
    "أحمد",
    "عبدالله",
    "عبدالعزيز",
    "خالد",
    "سعود",
    "فهد",
    "سلطان",
    "ناصر",
    "بندر",
    "تركي",
    "فيصل",
    "عمر",
    "يوسف",
    "إبراهيم",
    "سعد",
    "ماجد",
    "طلال",
    "وليد",
    "زياد",
    "رائد",
    "مشعل",
    "نايف",
    "عبدالرحمن",
]
FEMALE_FIRST = [
    "نورة",
    "سارة",
    "فاطمة",
    "عائشة",
    "منى",
    "هيا",
    "لمياء",
    "ريم",
    "أمل",
    "جواهر",
    "مها",
    "دلال",
    "شهد",
    "لطيفة",
    "حصة",
    "العنود",
    "غادة",
    "رنا",
    "وفاء",
    "أسماء",
    "هند",
    "بشرى",
]
FAMILY = [
    "القحطاني",
    "الغامدي",
    "الشمري",
    "العتيبي",
    "الدوسري",
    "الحربي",
    "المطيري",
    "الزهراني",
    "الشهري",
    "البقمي",
    "السبيعي",
    "العنزي",
    "الرشيدي",
    "الخالدي",
    "المالكي",
    "الجهني",
    "السلمي",
    "العمري",
    "الأحمدي",
    "الفيفي",
    "البلوي",
]
DEPARTMENTS = [
    "الموارد البشرية",
    "المالية",
    "تقنية المعلومات",
    "المبيعات",
    "التسويق",
    "العمليات",
    "المشتريات",
    "الشؤون القانونية",
    "خدمة العملاء",
    "الإنتاج",
    "الجودة",
    "الأمن والسلامة",
]
# Notes deliberately mix an Arabic sentence with Latin codes/digits to stress bidi.
NOTE_TEMPLATES = [
    "تم تجديد العقد رقم CT-{y}-{n} بتاريخ {d}.",
    "المنتج SKU-{n} بكمية {q} وحدة في المستودع WH-{w}.",
    "طلب إجازة رقم LR{n} لمدة {q} أيام — بانتظار الموافقة.",
    "رقم الطلب PO#{n} من المورّد VEND-{w} بمبلغ {q}00 ريال.",
    "ترقية إلى الدرجة G{w} اعتباراً من {d} (مرجع HR-{n}).",
    "مشروع Project-X المرحلة {w}: نسبة الإنجاز {q}%.",
]
# Curated edge cases: (name, note) — targets for search-normalization tests.
EDGE_CASES = [
    ("مدرسة الأمل", "تحقق من مطابقة مدرسه ↔ مدرسة (تاء مربوطة)."),
    ("أحمد المنصور", "تحقق من مطابقة احمد ↔ أحمد (همزة/ألف)."),
    ("إبراهيم الحسن", "تحقق من مطابقة ابراهيم ↔ إبراهيم."),
    ("آمنة القرشي", "تحقق من مطابقة امنه ↔ آمنة (مدّة + تاء مربوطة)."),
    ("مُحَمَّد بالتشكيل", "تحقق من تجاهل التشكيل (fatha/damma/shadda)."),
    ("محــمــد بالتطويل", "تحقق من تجاهل التطويل ـــ (tatweel)."),
    ("القرآن الكريم", "تحقق من مطابقة القران ↔ القرآن."),
    ("عيسى بن مريم", "تحقق من مطابقة عيسي ↔ عيسى (ألف مقصورة)."),
    ("مصطفى كامل", "تحقق من مطابقة مصطفي ↔ مصطفى."),
    ("رُقيّة السيد", "اسم يحتوي تشكيلاً جزئياً."),
    ("عبدالله ١٢٣", "ملاحظة تحتوي أرقاماً عربية ١٢٣ مقابل 123."),
    ("Ali (علي)", "اسم مختلط لاتيني/عربي لاختبار bidi في الخلية."),
]


def gregorian_to_hijri(g: date):
    """Dependency-free tabular (civil) Islamic conversion → (y, m, d).

    Good enough for realistic display in seed data. Phase 2 replaces the Hijri
    *field type* with a proper Umm al-Qura converter (hijri-converter); this
    helper is only for generating example strings and is not a source of truth.
    """

    gy, gm, gd = g.year, g.month, g.day
    jd = (
        (1461 * (gy + 4800 + (gm - 14) // 12)) // 4
        + (367 * (gm - 2 - 12 * ((gm - 14) // 12))) // 12
        - (3 * ((gy + 4900 + (gm - 14) // 12) // 100)) // 4
        + gd
        - 32075
    )
    l = jd - 1948440 + 10632
    n = (l - 1) // 10631
    l = l - 10631 * n + 354
    j = ((10985 - l) // 5316) * ((50 * l) // 17719) + (l // 5670) * ((43 * l) // 15238)
    l = (
        l
        - ((30 - j) // 15) * ((17719 * j) // 50)
        - (j // 16) * ((15238 * j) // 43)
        + 29
    )
    im = (24 * l) // 709
    id_ = l - (709 * im) // 24
    iy = 30 * n + j - 30
    return iy, im, id_


class Command(BaseCommand):
    help = "Seed a realistic Arabic dataset (default 50,000 rows) for testing."

    def add_arguments(self, parser):
        parser.add_argument("--rows", type=int, default=50000)
        parser.add_argument("--batch-size", type=int, default=2000)
        parser.add_argument(
            "--user-email",
            type=str,
            default=None,
            help="Owner of the created data. Defaults to the first superuser.",
        )
        parser.add_argument(
            "--workspace-name", type=str, default="Jadawel Seed / بيانات جداول"
        )
        parser.add_argument("--table-name", type=str, default="الموظفون")
        parser.add_argument(
            "--seed", type=int, default=1337, help="RNG seed for reproducibility."
        )

    def handle(self, *args, **options):
        rows = options["rows"]
        batch_size = max(1, options["batch_size"])
        rng = random.Random(options["seed"])  # nosec - deterministic test data

        user = self._resolve_user(options["user_email"])

        self.stdout.write(f"Owner: {user.email}")
        workspace = (
            CoreHandler()
            .create_workspace(user, name=options["workspace_name"])
            .workspace
        )
        database = CoreHandler().create_application(
            user,
            workspace,
            type_name=DatabaseApplicationType.type,
            name="قاعدة بيانات تجريبية",
        )

        fields = [
            ("الاسم", "text", {}),
            ("رقم الإقامة", "text", {}),
            ("القسم", "text", {}),
            (
                "تاريخ التعيين",
                "date",
                {"date_format": "ISO", "date_include_time": False},
            ),
            ("التاريخ الهجري", "text", {}),
            ("ملاحظات", "long_text", {}),
        ]
        table = TableHandler().create_table_and_fields(
            user, database, name=options["table_name"], fields=fields
        )
        self.stdout.write(
            self.style.SUCCESS(f"Created table id={table.id} with {len(fields)} fields")
        )

        model = table.get_model()
        attr = {
            fo["field"].name: f"field_{fid}" for fid, fo in model._field_objects.items()
        }

        set_owner = {}
        if hasattr(model, "created_by_id"):
            set_owner["created_by"] = user
        if hasattr(model, "last_modified_by_id"):
            set_owner["last_modified_by"] = user

        tick = time.time()
        created_total = 0
        all_row_ids = []
        order = Decimal("0")

        def make_instance(order_val, name, iqama, dept, greg, hijri, note):
            return model(
                order=order_val,
                **{
                    attr["الاسم"]: name,
                    attr["رقم الإقامة"]: iqama,
                    attr["القسم"]: dept,
                    attr["تاريخ التعيين"]: greg,
                    attr["التاريخ الهجري"]: hijri,
                    attr["ملاحظات"]: note,
                },
                **set_owner,
            )

        buffer = []

        def flush():
            nonlocal created_total, buffer
            if not buffer:
                return
            with transaction.atomic():
                created = model.objects.bulk_create(buffer, batch_size=1000)
            all_row_ids.extend(r.id for r in created)
            created_total += len(created)
            buffer = []
            self.stdout.write(f"  inserted {created_total}/{rows}")

        today = date.today()
        for i in range(rows):
            order += Decimal("1")
            if i < len(EDGE_CASES):
                name, note = EDGE_CASES[i]
            else:
                if rng.random() < 0.5:
                    first = rng.choice(MALE_FIRST)
                else:
                    first = rng.choice(FEMALE_FIRST)
                name = f"{first} {rng.choice(FAMILY)}"
                note = rng.choice(NOTE_TEMPLATES).format(
                    y=rng.randint(2019, 2025),
                    n=rng.randint(1000, 99999),
                    q=rng.randint(1, 90),
                    w=rng.randint(1, 12),
                    d=(today - timedelta(days=rng.randint(0, 3650))).isoformat(),
                )
            iqama = str(rng.choice([1, 2])) + "".join(
                str(rng.randint(0, 9)) for _ in range(9)
            )
            dept = rng.choice(DEPARTMENTS)
            greg = today - timedelta(days=rng.randint(0, 365 * 8))
            hy, hm, hd = gregorian_to_hijri(greg)
            hijri = f"{hy:04d}-{hm:02d}-{hd:02d}"
            buffer.append(make_instance(order, name, iqama, dept, greg, hijri, note))
            if len(buffer) >= batch_size:
                flush()
        flush()

        self.stdout.write("Updating full-text search data (may take a while)...")
        # create_table_and_fields builds the table schema but does not create the
        # per-workspace search table (database_search_workspace_<id>_data); that
        # normally happens on the first API row write. Ensure it exists before we
        # populate tsvectors, and don't let a search hiccup lose the seeded rows.
        try:
            SearchHandler.create_workspace_search_table_if_not_exists(workspace.id)
            SearchHandler.update_search_data(table, row_ids=all_row_ids)
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(
                self.style.WARNING(
                    f"Search data update failed ({exc}). Rows are inserted; run "
                    f"`./jadawel sync_table_tsvectors {table.id}` to populate search."
                )
            )

        tock = time.time()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_total} rows into table {table.id} "
                f"(workspace {workspace.id}, database {database.id}) "
                f"in {tock - tick:.1f}s."
            )
        )

    def _resolve_user(self, email):
        if email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist as exc:
                raise CommandError(f"No user with email {email!r}.") from exc
        user = User.objects.filter(is_superuser=True).order_by("id").first()
        if user is None:
            raise CommandError(
                "No superuser found. Create one first (./jadawel createsuperuser) "
                "or pass --user-email."
            )
        return user
