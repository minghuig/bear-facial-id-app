param(
  [Parameter(Mandatory=$true)][string]$Models,
  [Parameter(Mandatory=$true)][string]$Prototype,
  [int[]]$MemoryGiB = @(4, 2),
  [int]$ReserveMiB = 768,
  [string]$OutputDirectory = '.private/lightsail-results'
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$Models = (Resolve-Path $Models).Path
$Prototype = (Resolve-Path $Prototype).Path
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null
$results = @()
foreach ($limit in $MemoryGiB) {
  foreach ($stage in @('detection', 'recognition')) {
    $image = if ($stage -eq 'detection') { 'only-bears-local-cpu-detector' } else { 'only-bears-local-cpu-recognition' }
    $inputs = if ($stage -eq 'detection') {
      @('/inputs/artifacts/detector_pilot/images/p002.jpg', '/inputs/artifacts/detector_pilot/images/p012.jpg')
    } else {
      @('/inputs/artifacts/field_photo_test_v1/crops/q001.jpg', '/inputs/artifacts/field_photo_test_v1/crops/q002.jpg', '/inputs/artifacts/field_photo_test_v1/crops/q003.jpg')
    }
    $name = 'bear-lightsail-probe-' + [Guid]::NewGuid().ToString('N').Substring(0,10)
    $label = "$limit-gib-$stage"
    $start = Get-Date
    try {
      & docker run --name $name --network none --cpus 2 --memory "$($limit)g" --memory-swap "$($limit)g" `
        --mount "type=bind,source=$repo,target=/source,readonly" `
        --mount "type=bind,source=$Models,target=/models,readonly" `
        --mount "type=bind,source=$Prototype,target=/inputs,readonly" `
        -e MODEL_DIR=/models -e OMP_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e WANDB_MODE=disabled `
        --entrypoint python $image /source/experiments/lightsail/probe.py $stage --reserve-mib $ReserveMiB @inputs `
        1> (Join-Path $OutputDirectory "$label.jsonl") 2> (Join-Path $OutputDirectory "$label.stderr.txt")
      $exit = $LASTEXITCODE
      $info = (& docker inspect $name | ConvertFrom-Json)[0]
      $row = [ordered]@{ stage=$stage; memory_gib=$limit; reserve_mib=$ReserveMiB; exit_code=$exit;
        oom_killed=$info.State.OOMKilled; image_id=$info.Image; seconds=[Math]::Round(((Get-Date)-$start).TotalSeconds, 2) }
      $results += $row
      $row | ConvertTo-Json -Compress | Write-Output
    } finally {
      & docker rm -f $name | Out-Null
    }
  }
}
$results | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $OutputDirectory 'summary.json')
