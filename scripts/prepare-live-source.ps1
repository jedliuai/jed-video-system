param([string]$LocalConfig = (Join-Path $PSScriptRoot '../config/local.json'))
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskConfig = Get-Content -LiteralPath $LocalConfig -Raw | ConvertFrom-Json
$taskSource = $taskConfig.source
if (-not (Test-Path -LiteralPath $taskSource.originalVideo -PathType Leaf)) { throw 'Configure source.originalVideo first.' }
if ($taskSource.publicFile -ne 'live-source.mp4') { throw 'This pilot expects the staged file live-source.mp4.' }
$taskPublicFile = Join-Path $taskRoot 'motion-lab/public/live-source.mp4'
$taskManifest = Join-Path $taskRoot 'work/manifests/live-source.json'
New-Item -ItemType Directory -Force -Path (Split-Path $taskPublicFile),(Split-Path $taskManifest) | Out-Null
$taskOriginalHash = (Get-FileHash -LiteralPath $taskSource.originalVideo -Algorithm SHA256).Hash.ToLowerInvariant()
$taskReuse = $false
if ((Test-Path -LiteralPath $taskManifest) -and (Test-Path -LiteralPath $taskPublicFile)) {
  $taskPrevious = Get-Content -LiteralPath $taskManifest -Raw | ConvertFrom-Json
  $taskReuse = $taskPrevious.originalSha256 -eq $taskOriginalHash -and $taskPrevious.startSeconds -eq $taskSource.startSeconds -and $taskPrevious.durationSeconds -eq $taskSource.durationSeconds -and $taskPrevious.stagedSha256 -eq (Get-FileHash -LiteralPath $taskPublicFile -Algorithm SHA256).Hash.ToLowerInvariant()
}
if (-not $taskReuse) {
  & ffmpeg -hide_banner -loglevel error -y -ss $taskSource.startSeconds -i $taskSource.originalVideo -t $taskSource.durationSeconds -r 30 -fps_mode cfr -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart -threads 4 $taskPublicFile
  if ($LASTEXITCODE -ne 0) { throw 'Clean source extraction failed.' }
}
@{
  schemaVersion='0.1.0'; originalPath=$taskSource.originalVideo; originalSha256=$taskOriginalHash
  startSeconds=$taskSource.startSeconds; durationSeconds=$taskSource.durationSeconds
  stagedPath=$taskPublicFile; stagedSha256=(Get-FileHash -LiteralPath $taskPublicFile -Algorithm SHA256).Hash.ToLowerInvariant()
  fps=30; playbackRate=1; contentCutsAdded=$false; cacheReused=$taskReuse
} | ConvertTo-Json | Set-Content -LiteralPath $taskManifest -Encoding utf8
& $taskConfig.videoUse.python (Join-Path $PSScriptRoot 'verify-source-audio.py') --reference $taskSource.referenceVideo --candidate $taskPublicFile --output (Join-Path $taskRoot 'work/manifests/source-alignment.json')
if ($LASTEXITCODE -ne 0) { throw 'Reference transcript and clean media timing do not match.' }
