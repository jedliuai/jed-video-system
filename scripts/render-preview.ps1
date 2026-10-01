param([string]$LocalConfig = (Join-Path $PSScriptRoot 'preview-local.json'))
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskConfig = Get-Content -LiteralPath $LocalConfig -Raw | ConvertFrom-Json
$taskBrowser = $taskConfig.browserExecutable
if (-not (Test-Path -LiteralPath $taskBrowser -PathType Leaf)) { throw 'Configure an existing Chrome executable in preview-local.json.' }
$taskOutput = Join-Path $taskRoot 'work/previews'
New-Item -ItemType Directory -Force -Path $taskOutput | Out-Null
$taskSamples = @(
  @{Id='TalkingHeadA'; File='talking-head-a.png'},
  @{Id='ComparisonA'; File='comparison-a.png'},
  @{Id='TutorialA'; File='tutorial-a.png'},
  @{Id='TalkingHeadB'; File='talking-head-b.png'}
)
Push-Location (Join-Path $taskRoot 'motion-lab')
try {
  & npm run lint
  if ($LASTEXITCODE -ne 0) { throw 'Remotion source checks failed.' }
  foreach ($taskSample in $taskSamples) {
    & npx remotion still $taskSample.Id (Join-Path $taskOutput $taskSample.File) --frame=150 --browser-executable $taskBrowser --log=error
    if ($LASTEXITCODE -ne 0) { throw "Still render failed: $($taskSample.Id)" }
  }
  & npx remotion render JedStyleReel (Join-Path $taskOutput 'jed-style-preview.mp4') --codec=h264 --crf=18 --concurrency=4 --browser-executable $taskBrowser --log=warn
  if ($LASTEXITCODE -ne 0) { throw 'Video render failed.' }
  & npx remotion render TalkingHeadB (Join-Path $taskOutput 'talking-head-b.mp4') --codec=h264 --crf=18 --concurrency=4 --browser-executable $taskBrowser --log=warn
  if ($LASTEXITCODE -ne 0) { throw 'AGY video render failed.' }
} finally { Pop-Location }
Write-Output "Preview outputs: $taskOutput"
