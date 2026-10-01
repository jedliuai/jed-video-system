param(
  [string]$LocalConfig = (Join-Path $PSScriptRoot '../config/local.json'),
  [switch]$Publish
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskConfig = Get-Content -LiteralPath $LocalConfig -Raw | ConvertFrom-Json
$taskDate = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow,'China Standard Time').ToString('yyyyMMdd')
$taskName = 'jed-probe-live-' + $taskDate + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$taskSpec = @{
  schemaVersion='jed-draft-preview/1'; bridgeProject=$taskConfig.jianying.bridgeProject
  bridgeConfig=$taskConfig.jianying.bridgeConfig; outputRoot=(Join-Path $taskRoot 'work/compatibility/draft-builds')
  name=$taskName; source=(Join-Path $taskRoot 'motion-lab/public/live-source.mp4')
  overlay=(Join-Path $taskRoot 'work/renders/talking-head-overlay.mov')
  font=(Join-Path $taskRoot 'motion-lab/public/fonts/jed-sans-regular.ttf')
  renderProps=(Join-Path $taskRoot 'work/plans/live-render-props.json')
}
foreach ($taskKey in @('source','overlay','font','renderProps')) {
  if (-not (Test-Path -LiteralPath $taskSpec[$taskKey] -PathType Leaf)) { throw "Render the pilot first: missing $taskKey" }
}
$taskProps = Get-Content -LiteralPath $taskSpec.renderProps -Raw | ConvertFrom-Json
$taskSpec.overlayDurationFrames = [int](($taskProps.overlays | ForEach-Object { $_.outputStartFrame + $_.durationInFrames } | Measure-Object -Maximum).Maximum)
$taskInput = Join-Path $taskRoot ('work/compatibility/'+$taskName+'-input.json')
$taskResult = Join-Path $taskRoot ('work/compatibility/'+$taskName+'-result.json')
$taskSpec | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $taskInput -Encoding utf8
$taskArguments = @((Join-Path $taskRoot 'workers/draft-adapter/worker.py'),'preview','--input',$taskInput)
if ($Publish) { $taskArguments += '--publish' }
$taskResponse = & $taskConfig.jianying.python @taskArguments
if ($LASTEXITCODE -ne 0) { throw 'New-draft adapter failed; retained invocation evidence for review.' }
($taskResponse | Out-String) | Set-Content -LiteralPath $taskResult -Encoding utf8
$taskData = $taskResponse | Out-String | ConvertFrom-Json
Write-Output ('Draft: '+$taskData.name)
Write-Output ('Path: '+$taskData.draftPath)
Write-Output ('Published: '+$taskData.published)
Write-Output ('Evidence: '+$taskResult)
