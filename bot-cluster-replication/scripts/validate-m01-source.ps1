param(
  [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'
$taskPath = Join-Path $Root 'pilot/TASK-M01-SOURCE-INTAKE-001.yaml'
$evidencePath = Join-Path $Root 'pilot/EVIDENCE-RETURN-M01-SOURCE-INTAKE-001.yaml'
$reportPath = Join-Path $Root 'pilot/VERIFICATION-REPORT-M01-SOURCE-INTAKE-001.md'
$readbackPath = Join-Path $Root 'pilot/READBACK-M01-SOURCE-INTAKE-001.md'

foreach ($path in @($taskPath, $evidencePath, $reportPath, $readbackPath)) {
  if (-not (Test-Path -LiteralPath $path)) { throw "missing artifact: $path" }
}

$task = Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8
$evidence = Get-Content -LiteralPath $evidencePath -Raw -Encoding UTF8
$report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
$readback = Get-Content -LiteralPath $readbackPath -Raw -Encoding UTF8

foreach ($field in @(
  'task_id:', 'project_id:', 'agent_role_ref:', 'task_owner_ref:', 'input_refs:',
  'acceptance:', 'depends_on:', 'risk_level:', 'human_confirmation_required:',
  'output_refs:', 'evidence_return_ids:', 'blocked_reason:', 'retry_count:'
)) {
  if ($task -notmatch [regex]::Escape($field)) { throw "missing task field: $field" }
}

foreach ($field in @(
  'evidence_return_id:', 'source_object_id:', 'artifact_refs:', 'read_status:',
  'observed_result:', 'validation_status:', 'returned_at:', 'stable_source_url:'
)) {
  if ($evidence -notmatch [regex]::Escape($field)) { throw "missing evidence field: $field" }
}

foreach ($marker in @('M01 Source Intake Verification Report', 'KG-01 passed', 'KG-02 pending', 'TASK_REWORK', 'TASK_BLOCKED')) {
  if ($report -notmatch [regex]::Escape($marker)) { throw "missing report marker: $marker" }
}

foreach ($marker in @('task_id:', 'evidence_state:', 'validation_state:', 'rollback_state:')) {
  if ($readback -notmatch [regex]::Escape($marker)) { throw "missing readback field: $marker" }
}

if ($evidence -notmatch 'validation_status: pending') { throw 'M01 evidence must remain pending' }
if ($readback -notmatch 'kernel_gate_state: KG-01=passed, KG-02=pending') {
  throw 'M01 gate state must keep independent validation pending'
}

Write-Output 'M01 source intake control-plane checks: passed'
