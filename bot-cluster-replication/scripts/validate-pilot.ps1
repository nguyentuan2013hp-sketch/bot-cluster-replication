param(
  [string]$Root = (Join-Path $PSScriptRoot '..')
)
$ErrorActionPreference = 'Stop'
$task = Get-Content (Join-Path $Root 'pilot/TASK-FM001.yaml') -Raw
$evidence = Get-Content (Join-Path $Root 'pilot/EVIDENCE-RETURN-FM001.yaml') -Raw
$report = Get-Content (Join-Path $Root 'pilot/VERIFICATION-REPORT-FM001.md') -Raw
$readback = Get-Content (Join-Path $Root 'pilot/READBACK-FM001.md') -Raw
$requiredTaskFields = @('task_id:', 'project_id:', 'agent_role_ref:', 'task_owner_ref:', 'input_refs:', 'acceptance:', 'depends_on:', 'risk_level:', 'human_confirmation_required:', 'output_refs:', 'evidence_return_ids:', 'blocked_reason:', 'retry_count:')
$requiredEvidenceFields = @('evidence_return_id:', 'source_object_id:', 'artifact_refs:', 'read_status:', 'observed_result:', 'validation_status:', 'returned_at:')
foreach ($field in $requiredTaskFields) { if ($task -notmatch [regex]::Escape($field)) { throw "missing task field: $field" } }
foreach ($field in $requiredEvidenceFields) { if ($evidence -notmatch [regex]::Escape($field)) { throw "missing evidence field: $field" } }
foreach ($marker in @('正常路径', '缺资料/权限路径', '证据不足路径', '回退条件')) { if ($report -notmatch [regex]::Escape($marker)) { throw "missing verification marker: $marker" } }
foreach ($marker in @('task_id:', 'evidence_state:', 'validation_state:', 'rollback_state:')) { if ($readback -notmatch [regex]::Escape($marker)) { throw "missing readback field: $marker" } }
