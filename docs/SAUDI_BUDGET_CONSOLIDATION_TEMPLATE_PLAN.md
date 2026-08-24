# Saudi Budget Consolidation Template — Implementation Plan

## 1. Outcome

Add one bundled, Arabic-first Jadawel template named:

- Arabic: `تجميع واعتماد الميزانية`
- English/search name: `Saudi Budget Consolidation`
- Template slug/file: `saudi-budget-consolidation`

The template gives a Saudi private-sector finance team a simple workflow for
bringing differently structured Excel worksheets (through copy/paste) or CSV budget
files into one standard table,
classifying and validating the imported rows, consolidating only reviewed rows,
and presenting finance-recommended and board-approved totals.

This is an internal budgeting and governance template. It must be described as
`Saudi-aligned`, not as a system that certifies IFRS, SOCPA, ZATCA, tax, zakat, or
legal compliance.

## 2. Repository and delivery constraint

This checkout is the CranL deployment copy. Per `AGENTS.md`, feature work belongs
in the canonical `Azizahmed/Jadawel` repository first. The executor must:

1. Check the current repository and remotes before editing.
2. Prefer implementing and testing the template in the canonical repository.
3. Bring the completed commit into `jadawel_cranl` by the documented fast-forward
   release process.
4. Do not disturb unrelated uncommitted E2E work already present in this checkout.

If only this checkout is available, stop before implementation and obtain an
explicit override of the repository policy.

## 3. Product scope

### Included in the MVP

- One database application containing five related tables.
- One board dashboard application.
- Arabic table, field, view, option, widget, and sample-data labels.
- English and Arabic template-search keywords.
- Existing CSV import and Excel-compatible paste flow with manual column mapping.
- A raw/source value beside every standardized finance classification.
- Finance review status and formula-based validation status.
- Requested, finance-adjusted, recommended, and approved amounts.
- VAT treatment sufficient for budgeting, including recoverability.
- Consolidated views that include reviewed rows only.
- Fictional Saudi sample data in SAR.
- A targeted backend test that syncs and installs the template.

### Explicitly excluded

- A new `.xlsx` parser, general-purpose Excel importer, or AI mapping engine.
- Automatic interpretation of every source workbook.
- ERP, accounting system, ZATCA, or banking integrations.
- Statutory financial statements or three-statement forecasting.
- Government-sector or nonprofit accounting profiles.
- Legal electronic signatures, board quorum enforcement, or immutable legal
  records.
- Automatic locking of rows after approval.
- Changes under `premium/` or `enterprise/`; those packages are intentionally
  absent.
- Core `jadawel.*` edits unless a verified platform defect makes the template
  impossible. Any unavoidable core edit must be recorded in `PATCHES.md`.

## 4. Primary user journey

1. Finance creates or edits the seeded budget cycle.
2. Finance registers each received workbook in `ملفات الميزانية` and assigns it a
   short source code such as `IT-2027-V1`.
3. Finance opens `بنود الميزانية` and either imports a UTF-8 CSV or pastes copied
   cells from Excel using the existing import flow. The original `.xlsx` can still
   be attached to the file register for lineage.
4. In the existing import flow, finance maps each source column to the standard
   Jadawel fields. Unused source columns are ignored.
5. Imported source fields remain untouched. Finance fills the standardized
   account, cost center, VAT treatment, and review fields.
6. `حالة التحقق` explains whether a row is ready or what is missing.
7. The `صالح للتجميع` view contains only rows linked to a source file whose status is
   `صالح للتجميع`, and whose finance review and validation are complete.
8. The board dashboard reads only from consolidated/reviewed views.
9. Finance records the board decision, approval date, and resolution reference in
   `دورات الميزانية`.

Do not use import upsert for the default workflow. A newer workbook version must
remain a separate submission so that the previous source and its numbers are not
silently overwritten. Finance excludes superseded files by changing the source file
status; linked budget rows then fall out of the consolidated view without deletion.

## 5. Template metadata

Create `backend/templates/saudi-budget-consolidation.json` with:

```json
{
  "jadawel_template_version": 1,
  "name": "تجميع واعتماد الميزانية",
  "icon": "iconoir-bank",
  "categories": [
    "قوالب عربية",
    "Arabic templates",
    "Finance and Accounting"
  ],
  "keywords": [
    "ميزانية",
    "تجميع الميزانية",
    "اعتماد الميزانية",
    "المالية",
    "مجلس الإدارة",
    "السعودية",
    "budget",
    "budget consolidation",
    "finance",
    "board approval",
    "Saudi Arabia",
    "SAR"
  ],
  "open_application": "<exported board dashboard application id>",
  "export": []
}
```

Use the real exported numeric application ID for `open_application`. The template
sync code remaps it when the template is installed.

No companion ZIP is required unless the final sample contains an actual uploaded
file. Prefer an empty `file` field and no ZIP for this MVP.

## 6. Database application

Name the database application `تجميع الميزانية` and create the following tables in
this order.

### 6.1 `دورات الميزانية`

Purpose: one row per fiscal budget cycle and its board decision.

| Field | Type | Required behavior |
|---|---|---|
| اسم الدورة | Text, primary | Example: `ميزانية 2027` |
| السنة المالية | Number, 0 decimals | Use Western digits, e.g. `2027` |
| العملة | Single select | Seed `SAR - ريال سعودي` |
| الحالة | Single select | `مسودة`, `استقبال الملفات`, `مراجعة المالية`, `جاهزة للمجلس`, `معتمدة`, `مغلقة` |
| بداية التقديم | Date | ISO/Gregorian sample date |
| الموعد النهائي | Date | ISO/Gregorian sample date |
| تاريخ اعتماد المجلس | Date | Blank in the initial active cycle |
| رقم قرار المجلس | Text | Blank until approval |
| ملاحظات المجلس | Long text | Board conditions or requested changes |
| تعليمات الاستخدام | Long text | Short Arabic instructions for the workflow |

Views:

- `الدورة الحالية`: grid filtered to states other than `مغلقة`.
- `الدورات المعتمدة`: grid filtered to `معتمدة`.

Seed exactly one active fictional cycle and one previous approved cycle so that the
template is understandable in preview.

### 6.2 `دليل الحسابات الموحد`

Purpose: finance-controlled account mapping. Seed rows are illustrative and must
say so in the instructions; each organization replaces them with its approved
chart of accounts.

| Field | Type | Required behavior |
|---|---|---|
| رمز الحساب | Text, primary | Stable organization account code |
| اسم الحساب بالعربية | Text | Arabic account label |
| اسم الحساب بالإنجليزية | Text | English account label |
| التصنيف المالي | Single select | `الإيرادات`, `تكلفة الإيرادات`, `المصروفات التشغيلية`, `المصروفات الرأسمالية`, `التمويل`, `الزكاة والضرائب`, `أخرى` |
| نوع الميزانية | Single select | `OPEX`, `CAPEX`, `Revenue`, `Other` |
| معالجة VAT الافتراضية | Single select | `قياسية قابلة للاسترداد`, `قياسية غير قابلة للاسترداد`, `صفرية`, `معفاة`, `خارج النطاق` |
| نشط | Boolean | Inactive accounts must not be selected for new review work |
| ملاحظة التصنيف | Long text | Optional finance explanation |

Views:

- `الحسابات النشطة`.
- `حسب التصنيف المالي`, grouped by `التصنيف المالي`.
- `حسابات تحتاج مراجعة`, filtered where a required classification is blank.

Seed 10–15 fictional illustrative accounts covering revenue, payroll, rent,
software, professional services, travel, equipment, financing, and zakat/tax.

### 6.3 `الإدارات ومراكز التكلفة`

Purpose: finance-controlled organization dimension.

| Field | Type | Required behavior |
|---|---|---|
| رمز مركز التكلفة | Text, primary | Example: `CC-120` |
| اسم الإدارة | Text | Arabic department name |
| اسم الإدارة بالإنجليزية | Text | English department name |
| الكيان | Text | Legal entity or company name |
| المسؤول عن الميزانية | Text | Display name only; avoid real personal data |
| نشط | Boolean | Active mapping option |

Views:

- `المراكز النشطة`.
- `حسب الكيان`, grouped by `الكيان`.

Seed fictional Finance, Information Technology, Human Resources, Sales, and
Operations cost centers.

### 6.4 `ملفات الميزانية`

Purpose: one auditable register row per received Excel/CSV submission.

| Field | Type | Required behavior |
|---|---|---|
| رمز الملف | Text, primary | Example: `IT-2027-V1`; must be copied into imported line rows |
| دورة الميزانية | Link row, single | Links to `دورات الميزانية` |
| الإدارة | Link row, single | Links to `الإدارات ومراكز التكلفة` |
| اسم الملف الأصلي | Text | Original workbook filename |
| الملف الأصلي | File | Optional source attachment |
| رقم النسخة | Number, 0 decimals | Starts at `1` |
| إجمالي الملف المعلن | Number | SAR, 2 decimals |
| مقدم الملف | Text | Use fictional sample names only |
| تاريخ الاستلام | Date | |
| حالة الملف | Single select | `وارد`, `قيد المراجعة`, `صالح للتجميع`, `يحتاج تصحيح`, `مستبعد`, `استبدلته نسخة أحدث` |
| ملاحظات المراجعة | Long text | |

Views:

- `الملفات الواردة`.
- `تحتاج تصحيح`.
- `صالحة للتجميع`.
- `النسخ المستبعدة`.
- Optional form `تسجيل ملف ميزانية` for registering a new source file.

Seed several fictional files, including one superseded version, so the preview
demonstrates version lineage.

### 6.5 `بنود الميزانية`

Purpose: the single consolidated fact table. Keep source columns and finance-owned
standard columns visibly separate.

#### Source/imported fields

| Field | Type | Notes |
|---|---|---|
| معرف البند | Text, primary | Source row ID if available; otherwise finance assigns one |
| رمز الملف | Text | Plain text to make Excel mapping easy and preserve source lineage |
| السنة المالية | Number, 0 decimals | |
| الشهر | Single select | `يناير` through `ديسمبر` |
| الكيان الأصلي | Text | Value exactly as supplied |
| الإدارة الأصلية | Text | Value exactly as supplied |
| مركز التكلفة الأصلي | Text | Value exactly as supplied |
| رمز الحساب الأصلي | Text | Value exactly as supplied |
| اسم الحساب الأصلي | Text | Value exactly as supplied |
| وصف البند | Long text | |
| المبلغ المطلوب قبل VAT | Number | SAR, 2 decimals |
| ملاحظات المصدر | Long text | |

#### Finance-controlled standard fields

| Field | Type | Notes |
|---|---|---|
| دورة الميزانية | Link row, single | Required before review completes |
| ملف الميزانية | Link row, single | Links to `ملفات الميزانية`; finance matches it to the imported `رمز الملف` |
| حالة الملف | Lookup | From `ملف الميزانية`; only `صالح للتجميع` may reach board totals |
| الحساب الموحد | Link row, single | Links to `دليل الحسابات الموحد` |
| مركز التكلفة الموحد | Link row, single | Links to `الإدارات ومراكز التكلفة` |
| التصنيف المالي | Lookup | From the standardized account |
| نوع الميزانية | Lookup | `OPEX`, `CAPEX`, etc. from account |
| معالجة VAT | Single select | Same five options as the account default; finance confirms per line |
| نسبة VAT % | Number | 2 decimals; sample `15`, not `0.15` |
| تعديل المالية قبل VAT | Number | Positive or negative, SAR |
| سبب التعديل | Long text | Required by process when adjustment is nonzero |
| حالة مراجعة المالية | Single select | `غير مراجع`, `يحتاج استكمال`, `مراجع`, `مستبعد` |
| المبلغ المعتمد | Number | Blank until the board decision is recorded |

#### Formula/helper fields

Create and verify formulas equivalent to the following behavior. Use the actual
Jadawel formula syntax accepted by this checkout; copy patterns from existing
templates rather than guessing serialized formula metadata.

1. `صافي المبلغ قبل VAT`

   `المبلغ المطلوب قبل VAT + تعديل المالية قبل VAT`, treating blanks as zero.

2. `VAT غير القابل للاسترداد`

   If `معالجة VAT` is `قياسية غير قابلة للاسترداد`, calculate:
   `صافي المبلغ قبل VAT × نسبة VAT % ÷ 100`; otherwise zero.

3. `توصية المالية`

   `صافي المبلغ قبل VAT + VAT غير القابل للاسترداد`, rounded to 2 decimals.

4. `فرق المالية`

   `توصية المالية - المبلغ المطلوب قبل VAT`.

5. `حالة التحقق`

   Return one short Arabic result. Check in this order so the first result is
   actionable:

   - Missing source file code: `⚠️ رمز الملف مفقود`
   - Missing linked source-file register row: `⚠️ ملف الميزانية غير مربوط`
   - Linked source-file status is not `صالح للتجميع`: `⚠️ الملف غير صالح للتجميع`
   - Missing fiscal year or month: `⚠️ الفترة مفقودة`
   - Missing standardized account: `⚠️ الحساب غير موحد`
   - Missing standardized cost center: `⚠️ مركز التكلفة غير موحد`
   - Missing amount: `⚠️ المبلغ مفقود`
   - Missing VAT treatment: `⚠️ معالجة VAT مفقودة`
   - Nonzero finance adjustment with blank reason: `⚠️ سبب التعديل مفقود`
   - Finance status not reviewed: `⚠️ لم تكتمل المراجعة`
   - Otherwise: `✅ صالح للتجميع`

6. `المبلغ المعروض للمجلس`

   Use `المبلغ المعتمد` when present; otherwise use `توصية المالية`. This makes the
   pre-approval dashboard useful without losing the distinction between the two.

Do not attempt cross-row duplicate detection with a misleading formula. The MVP
preserves every version and relies on file status plus a grouped review view.

Views:

- `كل البنود`: all rows; source fields first, finance fields second.
- `تحتاج توحيد`: validation state contains an account/cost-center mapping warning.
- `أخطاء البيانات`: validation state is not `✅ صالح للتجميع`.
- `مراجعة المالية`: rows not marked `مراجع` or `مستبعد`.
- `صالح للتجميع`: validation state is `✅ صالح للتجميع`; this necessarily excludes
  source files marked superseded, excluded, or requiring correction.
- `مستبعد`: finance status is `مستبعد`.
- `حسب الإدارة`: valid rows grouped by standardized cost center.
- `حسب التصنيف`: valid rows grouped by financial classification.
- `جاهز للمجلس`: valid rows showing requested, adjustment, recommendation, approved
  amount, and reason.
- Optional form `إدخال بند يدوي` for exceptions that arrive outside Excel.

Seed 24–36 fictional rows across at least 3 departments, 6 accounts, and several
months. Include:

- Valid OPEX, CAPEX, and revenue rows.
- Recoverable and non-recoverable VAT examples.
- One missing account mapping.
- One missing cost-center mapping.
- One finance adjustment with a reason.
- One excluded row from a superseded file.
- Requested, recommended, and approved values that visibly differ.

The sample totals must be internally consistent and easy to verify manually.

## 7. Board dashboard application

Name the dashboard `ملخص الميزانية للمجلس`. Configure it against the installed
database through the existing local Jadawel integration.

Use only widget types available in this OSS fork:

- `summary`
- `chart`
- `records_list`
- `progress` only if its target has a real, understandable meaning

Recommended layout:

1. Summary: `إجمالي طلبات الإدارات` — sum requested amounts from valid/reviewed rows.
2. Summary: `توصية المالية` — sum finance recommendations from valid/reviewed rows.
3. Summary: `المبلغ المعتمد` — sum approved amounts, ignoring blanks.
4. Summary: `بنود تحتاج معالجة` — count rows from `أخطاء البيانات`.
5. Bar chart: `الميزانية حسب الإدارة` — board amount grouped by standardized cost
   center or department.
6. Doughnut or bar chart: `الميزانية حسب التصنيف` — board amount grouped by financial
   classification.
7. Bar chart: `طلبات الإدارات مقابل توصية المالية` if the grouped service supports
   the two series cleanly; otherwise omit it rather than adding custom code.
8. Records list: `أكبر التعديلات` — show source account, department, requested amount,
   finance recommendation, and reason, sorted by the best available variance field.
9. Records list: `مشكلات تمنع الاعتماد` — rows from `أخطاء البيانات`.

Every board total must use a filtered valid/reviewed view or equivalent data-source
filters. No invalid, superseded, or excluded line may affect a board number.

Set `open_application` to this dashboard so the installed template opens on the board
summary.

### Dashboard import caveat

During template gallery sync, the local integration may not have an authorized user.
On installation, `application_imported` assigns the installing user. The executor must
test both template sync and installed-template dashboard data-source remapping. If the
gallery preview cannot dispatch live data without a user, use supported data-source
sample data for preview; do not hardcode a real user or weaken permissions.

## 8. Saudi-alignment rules

Version one targets a private Saudi company or group.

- Default currency is SAR.
- Dates use the Gregorian fiscal calendar; Hijri is not forced.
- Account names are bilingual where useful, with Arabic shown first.
- Financial categories are management-reporting mappings inspired by the
  organization's SOCPA-endorsed IFRS or IFRS-for-SMEs chart of accounts.
- The sample chart is explicitly illustrative and replaceable.
- VAT treatment is configurable per line.
- `15%` appears only as sample/default input for a standard-rated line; it must not be
  automatically applied to exempt, zero-rated, out-of-scope, or fully recoverable VAT.
- Recoverable input VAT is excluded from the budgeted cost in the MVP; non-recoverable
  VAT is included.
- Zakat and tax can be represented as budget classifications, but the template does
  not calculate a tax or zakat liability.

Official references for wording and product notes:

- SOCPA accounting standards: https://socpa.org.sa/Socpa/Professional-standards/Accounting-standards.aspx?lang=en-us
- ZATCA VAT guidance: https://zatca.gov.sa/en/HelpCenter/guidelines/

Do not copy long text from those sites into the repository.

## 9. How to build the template artifact

Prefer creating a real workspace and exporting it instead of hand-authoring a large
cross-referenced JSON file.

1. Start the local stack and create a disposable workspace.
2. Build the database, tables, fields, formulas, views, filters, groupings, and sample
   rows through the UI or stable application APIs.
3. Build and connect the dashboard after the database is complete.
4. Export both applications together from that workspace. Database application IDs
   must be available before dashboard services are imported; core import ordering
   already prioritizes database applications.
5. Use the existing `create_template` management command with the export as the source,
   or wrap the exported application list manually in the metadata envelope above.
6. Set the final filename to `backend/templates/saudi-budget-consolidation.json`.
7. Set `open_application` to the exported dashboard ID.
8. Format the JSON consistently with existing templates.
9. Validate syntax with `jq empty backend/templates/saudi-budget-consolidation.json`.
10. Run a targeted sync:

    ```bash
    just b manage sync_templates --only '^saudi-budget-consolidation$' --force
    ```

11. Install it into a clean test workspace and visually check all applications,
    relations, formulas, views, dashboard data sources, and RTL presentation.

Do not retain disposable scripts, credentials, workspace exports, or sample source
files unless they are intentional reviewed artifacts.

## 10. Tests

Use the repository's `write-backend-unit-test` skill when implementing the targeted
pytest test.

Add `backend/tests/arabase/test_saudi_budget_template.py` with a focused integration
test that:

1. Syncs only `saudi-budget-consolidation`.
2. Finds the template by slug and confirms its Arabic name, categories, keywords, and
   dashboard `open_application`.
3. Installs it for a test user into a clean workspace.
4. Confirms exactly one database and one dashboard application are installed.
5. Confirms all five Arabic table names exist.
6. Confirms the required source, standardized, formula, and approval fields exist.
7. Confirms the required views exist and reference valid imported field IDs.
8. Confirms sample rows exist and at least one row evaluates to `✅ صالح للتجميع` and
   at least one evaluates to a warning.
9. Confirms the VAT/recommendation formulas produce expected values for one
   non-recoverable and one recoverable example.
10. Confirms the dashboard integration's authorized user is the installing user.
11. Confirms every dashboard service table/view/field ID points to the newly installed
    database objects, not the exported IDs.
12. Confirms no dashboard data source includes rows from an excluded/superseded file
    in its effective filter/view configuration.

If formula evaluation in the test requires a refresh/recalculation handler, use the
same pattern as existing formula field tests rather than asserting serialized formula
strings only.

Do not add a frontend test unless frontend code changes. A pure template addition
should not need frontend changes.

## 11. Verification commands

Run the smallest checks first, then the fork gates:

```bash
jq empty backend/templates/saudi-budget-consolidation.json
just b test tests/arabase/test_saudi_budget_template.py -q
just b test tests/arabase -q
just f yarn locale:check
```

The equivalent from `web-frontend/` is `yarn locale:check`. No locale files are
expected to change for a template-only implementation, but the fork gate must still
pass.

Also perform a manual RTL verification after installing the template:

- Arabic labels are not clipped.
- Grid columns and dashboard widgets read naturally in RTL.
- Western digits remain unchanged.
- `VAT`, `OPEX`, `CAPEX`, `SAR`, `SOCPA`, and `IFRS` remain Latin technical tokens.
- The template can still be found with English search keywords.

## 12. Acceptance criteria

The work is complete only when all of the following are true:

- The new template appears in Arabic and finance-related template categories.
- Installing it creates the database and dashboard without errors.
- A finance user can import a UTF-8 CSV or paste cells copied from Excel into
  `بنود الميزانية` using the existing import flow and map differently named source
  columns.
- Original source values remain visible after finance standardization.
- Invalid/unreviewed rows are visible in an error view and excluded from consolidated
  board totals.
- Recoverable VAT does not increase budgeted cost; non-recoverable standard-rate VAT
  does, based on the entered rate.
- Finance adjustments never overwrite the submitted amount and require a reason by
  validation rule.
- Requested, recommended, and approved values are separately visible.
- A superseded file can be excluded without deleting its rows.
- All board dashboard totals trace to valid/reviewed budget lines.
- Template sync, install, ID remapping, formulas, targeted tests, Arabic locale parity,
  and fork hygiene pass.
- No real company, employee, supplier, account, or financial data is committed.
- No claim of certified legal, accounting, VAT, zakat, SOCPA, or IFRS compliance is
  made.

## 13. Implementation sequence for Luna

1. Read `AGENTS.md` and this plan completely.
2. Verify the canonical repository/worktree and preserve unrelated changes.
3. Inspect the referenced template, import, formula, and dashboard implementations:
   - `backend/src/jadawel/core/handler.py`
   - `backend/src/jadawel/core/management/commands/create_template.py`
   - `backend/src/jadawel/core/management/commands/sync_templates.py`
   - `web-frontend/modules/database/components/table/ImportFileModal.vue`
   - `backend/src/jadawel/contrib/dashboard/application_types.py`
   - `backend/src/arabase/dashboard/widgets/widget_types.py`
   - `backend/templates/arabic-project-management.json`
   - `backend/templates/business-expenses.json`
4. Build the disposable source workspace and sample data.
5. Export it and create the final template JSON.
6. Add the targeted backend integration test.
7. Run targeted sync/install and tests.
8. Perform manual Arabic RTL and dashboard verification.
9. Review the diff for generated noise, real data, secrets, upstream-core edits, and
   accidental references to removed paid packages.
10. Report the changed files, checks run, exact results, and any intentionally deferred
    limitations.

Luna may make minor implementation adjustments when the actual field or dashboard
registries require them, but must preserve the product behavior and acceptance criteria
above. If meeting an acceptance criterion requires new core product code, stop and
report the gap before expanding scope.
