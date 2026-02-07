{{- define "sonarsniffer.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 -}}
{{- end -}}

{{- define "sonarsniffer.fullname" -}}
{{- printf "%s-%s" (include "sonarsniffer.name" .) .Release.Namespace | trunc 63 -}}
{{- end -}}

{{- define "sonarsniffer.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- printf "%s-sa" (include "sonarsniffer.name" .) -}}
{{- else -}}
{{- .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}