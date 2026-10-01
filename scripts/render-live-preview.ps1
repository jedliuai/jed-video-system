param(
  [string]$LocalConfig = (Join-Path $PSScriptRoot '../config/local.json'),
  [string]$Plan = (Join-Path $PSScriptRoot '../work/plans/live-edit-plan.json')
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskConfig = Get-Content -LiteralPath $LocalConfig -Raw | ConvertFrom-Json
$taskSource = Join-Path $taskRoot 'motion-lab/public/live-source.mp4'
$taskAlignment = Get-Content -LiteralPath (Join-Path $taskRoot 'work/manifests/source-alignment.json') -Raw | ConvertFrom-Json
if ($taskAlignment.status -ne 'passed' -or $taskAlignment.candidate.sha256 -ne (Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash.ToLowerInvariant()) { throw 'Run prepare-live-source.ps1 to verify this media before rendering.' }
if (-not (Test-Path -LiteralPath $taskConfig.remotion.browserExecutable -PathType Leaf)) { throw 'Configure an existing browser executable.' }
$taskTranscription = & python (Join-Path $taskRoot 'plugins/jed-video-system/scripts/transcribe.py') $taskConfig.source.referenceVideo --output-root (Join-Path $taskRoot 'work/transcripts') --skill-root $taskConfig.videoUse.skillRoot --python $taskConfig.videoUse.python --model-dir $taskConfig.videoUse.modelDirectory
if ($LASTEXITCODE -ne 0) { throw 'Transcription failed.' }
$taskTranscript = ($taskTranscription | Out-String | ConvertFrom-Json).normalizedTranscript
$taskPropsPath = Join-Path $taskRoot 'work/plans/live-render-props.json'
& python (Join-Path $taskRoot 'plugins/jed-video-system/scripts/compile_plan.py') --plan $Plan --transcript $taskTranscript --output $taskPropsPath
if ($LASTEXITCODE -ne 0) { throw 'Plan validation failed.' }
$taskProps = Get-Content -LiteralPath $taskPropsPath -Raw | ConvertFrom-Json
if ($taskProps.fps -ne 30) { throw 'This registered pilot composition uses 30fps.' }
$taskOverlayDuration = ($taskProps.overlays | ForEach-Object { $_.outputStartFrame + $_.durationInFrames } | Measure-Object -Maximum).Maximum
if ($taskOverlayDuration -le 0) { throw 'Pilot expects at least one validated overlay.' }
$taskOverlayProps = Join-Path $taskRoot 'work/plans/live-overlay-props.json'
@{overlays=$taskProps.overlays; durationInFrames=[int]$taskOverlayDuration} | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $taskOverlayProps -Encoding utf8
$taskOutputs = Join-Path $taskRoot 'work/renders'
New-Item -ItemType Directory -Force -Path $taskOutputs | Out-Null
Push-Location (Join-Path $taskRoot $taskConfig.remotion.project)
try {
  & npm run lint
  if ($LASTEXITCODE -ne 0) { throw 'Motion source validation failed.' }
  & npx remotion render ProductionOverlay (Join-Path $taskOutputs 'talking-head-overlay.mov') --props $taskOverlayProps --image-format=png --pixel-format=yuva444p10le --codec=prores --prores-profile=4444 --concurrency=4 --browser-executable $taskConfig.remotion.browserExecutable --log=error
  if ($LASTEXITCODE -ne 0) { throw 'Isolated alpha overlay failed.' }
  Write-Output 'Production alpha overlay ready.'
  & npx remotion render ProductionPreview (Join-Path $taskOutputs 'jed-live-preview-remotion.mp4') --props $taskPropsPath --codec=h264 --crf=18 --concurrency=4 --browser-executable $taskConfig.remotion.browserExecutable --log=error
  if ($LASTEXITCODE -ne 0) { throw 'Real-video preview failed.' }
  & $taskConfig.videoUse.python (Join-Path $PSScriptRoot 'normalize-preview-audio.py') --reference $taskSource --input (Join-Path $taskOutputs 'jed-live-preview-remotion.mp4') --output (Join-Path $taskOutputs 'jed-live-preview.mp4') --props $taskPropsPath --report (Join-Path $taskRoot 'work/manifests/preview-audio-correction.json')
  if ($LASTEXITCODE -ne 0) { throw 'Final audio clock verification failed.' }
  & npx remotion still ProductionPreview (Join-Path $taskOutputs 'jed-live-preview.png') --props $taskPropsPath --frame=180 --browser-executable $taskConfig.remotion.browserExecutable --log=error
  if ($LASTEXITCODE -ne 0) { throw 'Real-video poster failed.' }
} finally { Pop-Location }
Write-Output "Live preview rendered in $taskOutputs"
