{{- /*
  Common Helm template helpers for RecipeLens.
*/ -}}

{{/*
Expand the name of the chart.
*/}}
{{- define "recipelens.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully-qualified app name.
*/}}
{{- define "recipelens.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to all resources.
*/}}
{{- define "recipelens.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "recipelens.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end }}

{{/*
Selector labels — used in matchLabels (must be stable across upgrades).
*/}}
{{- define "recipelens.selectorLabels" -}}
app.kubernetes.io/name: {{ include "recipelens.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend-specific selector labels.
*/}}
{{- define "recipelens.backend.selectorLabels" -}}
{{ include "recipelens.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend-specific selector labels.
*/}}
{{- define "recipelens.frontend.selectorLabels" -}}
{{ include "recipelens.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Backend image reference — registry/repository:tag.
Fails at render time if the tag is empty to prevent accidental 'latest' pulls.
*/}}
{{- define "recipelens.backend.image" -}}
{{- if not .Values.backend.image.tag }}
{{- fail "backend.image.tag must be set — do not use an empty tag" }}
{{- end }}
{{- printf "%s/%s:%s" .Values.registry .Values.backend.image.repository .Values.backend.image.tag }}
{{- end }}

{{/*
Frontend image reference — registry/repository:tag.
*/}}
{{- define "recipelens.frontend.image" -}}
{{- if not .Values.frontend.image.tag }}
{{- fail "frontend.image.tag must be set — do not use an empty tag" }}
{{- end }}
{{- printf "%s/%s:%s" .Values.registry .Values.frontend.image.repository .Values.frontend.image.tag }}
{{- end }}
