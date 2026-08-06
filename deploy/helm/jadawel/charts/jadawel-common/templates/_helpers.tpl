{{/*
Expand the name of the chart.
*/}}
{{- define "jadawel.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Expand the namespace of the chart.
*/}}
{{- define "jadawel.namespace" -}}
{{- default .Release.Namespace .Values.namespace }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "jadawel.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "jadawel.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "jadawel.additionalLabels" }}
{{- range $key, $val := .Values.additionalLabels }}
{{ $key }}: {{ $val }}
{{- end }}
{{- end }}

{{- define "jadawel.additionalSelectorLabels" }}
{{- range $key, $val := .Values.additionalSelectorLabels }}
{{ $key }}: {{ $val }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "jadawel.labels" -}}
helm.sh/chart: {{ include "jadawel.chart" . }}
{{ include "jadawel.selectorLabels" . }}
{{- include "jadawel.additionalLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "jadawel.selectorLabels" -}}
app.kubernetes.io/name: {{ include "jadawel.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- include "jadawel.additionalSelectorLabels" . }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "jadawel.serviceAccountName" -}}
{{- if not .Values.global.jadawel.serviceAccount.shared -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "jadawel.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{ else }}
{{- default "default" .Values.global.jadawel.serviceAccount.name }}
{{- end }}
{{- end }}


{{/*
Create command for readiness probe
*/}}
{{- define "jadawel.readinessProbeCommand" -}}
{{- $command := .Values.readinessProbe.command }}
{{- if $command }}
{{- printf "command:" | nindent 4 -}}
{{- toYaml $command | nindent 6 -}}
{{ else }}
{{- printf "command:" | nindent 4 -}}
{{- printf "- /bin/bash" | nindent 6 -}}
{{- printf "- -c" | nindent 6 -}}
{{- printf "- /jadawel/backend/docker/docker-entrypoint.sh backend-healthcheck" | nindent 6 -}}
{{- end }}
{{- end }}

{{/*
Create full readinessProbe
*/}}
{{- define "jadawel.readinessProbe" -}}
{{- if .Values.readinessProbe }}
readinessProbe:
  exec: {{ include "jadawel.readinessProbeCommand" . }}
  initialDelaySeconds: {{ .Values.readinessProbe.initialDelaySeconds }}
  periodSeconds: {{ .Values.readinessProbe.periodSeconds }}
  timeoutSeconds: {{ .Values.readinessProbe.timeoutSeconds }}
  successThreshold: {{ .Values.readinessProbe.successThreshold }}
  failureThreshold: {{ .Values.readinessProbe.failureThreshold }}
{{- end }}
{{- end }}

{{/*
Create command for liveness probe
*/}}
{{- define "jadawel.livenessProbeCommand" -}}
{{- $command := .Values.livenessProbe.command }}
{{- if $command }}
{{- printf "command:" | nindent 4 -}}
{{- toYaml $command | nindent 6 -}}
{{ else }}
{{- printf "command:" | nindent 4 -}}
{{- printf "- /bin/bash" | nindent 6 -}}
{{- printf "- -c" | nindent 6 -}}
{{- printf "- /jadawel/backend/docker/docker-entrypoint.sh backend-healthcheck" | nindent 6 -}}
{{- end }}
{{- end }}

{{/*
Create full livenessProbe
*/}}
{{- define "jadawel.livenessProbe" -}}
{{- if .Values.livenessProbe }}
livenessProbe:
  exec: {{ include "jadawel.livenessProbeCommand" . }}
  initialDelaySeconds: {{ .Values.livenessProbe.initialDelaySeconds }}
  periodSeconds: {{ .Values.livenessProbe.periodSeconds }}
  timeoutSeconds: {{ .Values.livenessProbe.timeoutSeconds }}
  successThreshold: {{ .Values.livenessProbe.successThreshold }}
  failureThreshold: {{ .Values.livenessProbe.failureThreshold }}
{{- end }}
{{- end }}

{{/*
Image Pull secrets combine the global and local imagePullSecrets
*/}}
{{- define "jadawel.imagePullSecrets" -}}
{{- $global := .Values.global.jadawel.imagePullSecrets }}
{{- $local := .Values.imagePullSecrets }}
{{- if and $global $local }}
{{- $all := concat $global $local -}}
{{- toYaml $all | nindent 8}}
{{- else if $global }}
{{- toYaml $global | nindent 8}}
{{- else if $local }}
{{- toYaml $local | nindent 8}}
{{- end }}
{{- end }}

{{/*
Create image url to use
*/}}
{{- define "jadawel.image" -}}
{{- if and .Values.global.jadawel.imageRegistry .Values.global.jadawel.image.tag -}}
{{- printf "%s/%s:%s" .Values.global.jadawel.imageRegistry .Values.image.repository .Values.global.jadawel.image.tag }}
{{- else -}}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag }}
{{- end }}
{{- end }}

{{/*
Create envFrom options
*/}}
{{- define "jadawel.envFrom" -}}
{{- if .Values.mountConfiguration.backend }}
- configMapRef:
    name: {{ .Values.global.jadawel.sharedConfigMap }}
- configMapRef:
    name: {{ .Values.global.jadawel.backendConfigMap }}
- secretRef:
    name: {{ .Values.global.jadawel.backendSecret }}
{{ end }}
{{- if .Values.mountConfiguration.frontend }}
- configMapRef:
    name: {{ .Values.global.jadawel.sharedConfigMap }}
- configMapRef:
    name: {{ .Values.global.jadawel.frontendConfigMap }}
{{ end }}
{{- if .Values.global.jadawel.envFrom }}
{{ toYaml .Values.global.jadawel.envFrom }}
{{- end }}
{{- if .Values.envFrom }}
{{ toYaml .Values.envFrom }}
{{- end }}
{{- end }}

{{/*
PodSecurityContext combine the global and local PodSecurityContexts
*/}}
{{- define "jadawel.podSecurityContext" -}}
{{- if .Values.securityContext.enabled }}
{{- omit .Values.securityContext "enabled" | toYaml  }}
{{- else if .Values.global.jadawel.securityContext.enabled }}
{{- omit .Values.global.jadawel.securityContext "enabled" | toYaml }}
{{- end }}
{{- end }}

{{/*
ContainerSecurityContext combine the global and local ContainerSecurityContexts
*/}}
{{- define "jadawel.containerSecurityContext" -}}
{{- if .Values.containerSecurityContext.enabled }}
{{- omit .Values.containerSecurityContext "enabled" | toYaml  }}
{{- else if .Values.global.jadawel.containerSecurityContext.enabled }}
{{- omit .Values.global.jadawel.containerSecurityContext "enabled" | toYaml }}
{{- end }}
{{- end }}
