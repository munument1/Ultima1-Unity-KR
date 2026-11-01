param([string]$GameDir=$PSScriptRoot,[switch]$VerifyOnly,[switch]$Restore)
$ErrorActionPreference='Stop'
function Hash([string]$p) { $s=[IO.File]::OpenRead($p); $h=[Security.Cryptography.SHA256]::Create(); try { [BitConverter]::ToString($h.ComputeHash($s)).Replace('-','').ToLowerInvariant() } finally { $s.Dispose(); $h.Dispose() } }
$GameDir=[IO.Path]::GetFullPath($GameDir)
$m=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'patch.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$payload=Join-Path $PSScriptRoot 'patch.bin'
if ((Hash $payload) -ne $m.payload_sha256) { throw 'Patch payload checksum mismatch.' }
if (-not (Test-Path -LiteralPath (Join-Path $GameDir 'Ultima I Unity.exe'))) { throw 'Select the original game folder containing Ultima I Unity.exe.' }
if (Get-Process -Name 'Ultima I Unity' -ErrorAction SilentlyContinue) { throw 'Close Ultima I Unity before installing.' }
$plans=@()
foreach($f in $m.files) {
  $p=[IO.Path]::GetFullPath((Join-Path $GameDir $f.path))
  if (-not $p.StartsWith($GameDir.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe manifest path.' }
  $h=Hash $p; $backup=$p+'.u1k-original-v06'
  if ($Restore) {
    if ($h -eq $f.original_sha256) { continue }
    if ($h -ne $f.patched_sha256 -or (Hash $backup) -ne $f.original_sha256) { throw "Cannot safely restore: $p" }
  } else {
    if ($h -eq $f.patched_sha256) { continue }
    if ($h -ne $f.original_sha256) { throw "Unsupported original file; no files changed: $p" }
    if ((Test-Path -LiteralPath $backup) -and (Hash $backup) -ne $f.original_sha256) { throw "Existing backup mismatch: $backup" }
  }
  $plans+= [pscustomobject]@{file=$f;path=$p;backup=$backup;stage=$p+'.u1k-stage-'+[guid]::NewGuid().ToString('N')}
}
if ($VerifyOnly) { Write-Host "Verified supported files. Pending changes: $($plans.Count)"; exit 0 }
$committed=@()
try {
  foreach($plan in $plans) {
    if ($Restore) { [IO.File]::Copy($plan.backup,$plan.stage,$false); continue }
    $input=[IO.File]::OpenRead($plan.path); $data=[IO.File]::OpenRead($payload); $output=[IO.File]::Create($plan.stage)
    try {
      $buffer=New-Object byte[] 65536
      foreach($op in $plan.file.operations) {
        $stream=if($op[0] -eq 'copy'){$input}elseif($op[0] -eq 'data'){$data}else{throw 'Unknown delta operation'}
        [void]$stream.Seek([long]$op[1],[IO.SeekOrigin]::Begin); $remaining=[long]$op[2]
        while($remaining -gt 0) { $n=$stream.Read($buffer,0,[int][Math]::Min($remaining,$buffer.Length)); if($n -eq 0){throw 'Truncated delta input'}; $output.Write($buffer,0,$n); $remaining-=$n }
      }
    } finally { $input.Dispose(); $data.Dispose(); $output.Dispose() }
    if ((Get-Item -LiteralPath $plan.stage).Length -ne $plan.file.patched_size -or (Hash $plan.stage) -ne $plan.file.patched_sha256) { throw 'Reconstructed output checksum mismatch.' }
  }
  foreach($plan in $plans) {
    if (-not $Restore -and -not (Test-Path -LiteralPath $plan.backup)) { [IO.File]::Copy($plan.path,$plan.backup,$false) }
    # Track before copy so an interrupted/failed copy is also rolled back.
    if ($Restore) { $rollback=$plan.stage+'.rollback'; [IO.File]::Copy($plan.path,$rollback,$false) } else { $rollback=$plan.backup }
    $committed+= [pscustomobject]@{path=$plan.path;rollback=$rollback}
    [IO.File]::Copy($plan.stage,$plan.path,$true)
    $expected=if($Restore){$plan.file.original_sha256}else{$plan.file.patched_sha256}
    if ((Hash $plan.path) -ne $expected) { throw 'Installed checksum mismatch.' }
  }
  Write-Host "Completed v0.6. Changed files: $($plans.Count). Original backups retained."
} catch {
  foreach($c in $committed) { [IO.File]::Copy($c.rollback,$c.path,$true) }
  throw
} finally {
  foreach($plan in $plans) { if(Test-Path -LiteralPath $plan.stage){[IO.File]::Delete($plan.stage)}; $rb=$plan.stage+'.rollback'; if(Test-Path -LiteralPath $rb){[IO.File]::Delete($rb)} }
}
