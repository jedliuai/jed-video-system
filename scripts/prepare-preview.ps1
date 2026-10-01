param([string]$LocalConfig = (Join-Path $PSScriptRoot 'preview-local.json'))
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskConfig = Get-Content -LiteralPath $LocalConfig -Raw | ConvertFrom-Json
$taskPublic = Join-Path $taskRoot 'motion-lab/public'
$taskOutput = Join-Path $taskRoot 'work/previews'
foreach ($taskKey in @('sourceVideo', 'portrait', 'regularFont', 'boldFont')) {
  if (-not (Test-Path -LiteralPath $taskConfig.$taskKey -PathType Leaf)) { throw "Missing asset: $taskKey. Configure $LocalConfig first." }
}
New-Item -ItemType Directory -Force -Path (Join-Path $taskPublic 'fonts'), $taskOutput | Out-Null
Copy-Item -LiteralPath $taskConfig.regularFont -Destination (Join-Path $taskPublic 'fonts/jed-sans-regular.ttf')
Copy-Item -LiteralPath $taskConfig.boldFont -Destination (Join-Path $taskPublic 'fonts/jed-sans-bold.ttf')
Copy-Item -LiteralPath $taskConfig.portrait -Destination (Join-Path $taskPublic 'jed-portrait.png')
foreach ($taskSample in @(
  @{Name='talking-head.jpg'; Seconds=$taskConfig.talkingHeadSampleSeconds},
  @{Name='screen-recording.jpg'; Seconds=$taskConfig.screenRecordingSampleSeconds}
)) {
  & ffmpeg -hide_banner -loglevel error -y -ss $taskSample.Seconds -i $taskConfig.sourceVideo -frames:v 1 -q:v 2 (Join-Path $taskPublic $taskSample.Name)
  if ($LASTEXITCODE -ne 0) { throw "Frame extraction failed: $($taskSample.Name)" }
}
@{
  sourceVideo=$taskConfig.sourceVideo
  sourceSha256=(Get-FileHash -LiteralPath $taskConfig.sourceVideo -Algorithm SHA256).Hash
  talkingHeadSampleSeconds=$taskConfig.talkingHeadSampleSeconds
  screenRecordingSampleSeconds=$taskConfig.screenRecordingSampleSeconds
  kind='static-source-with-animated-overlays'
  narrationAligned=$false
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'source-manifest.json') -Encoding utf8
Write-Output 'Preview assets prepared.'
