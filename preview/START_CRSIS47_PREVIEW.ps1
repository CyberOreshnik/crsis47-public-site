$ErrorActionPreference = "Stop"
$root = (Resolve-Path $PSScriptRoot).Path
$port = 8768
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add("http://localhost:$port/")
try { $listener.Start() } catch { Write-Host "Could not start local preview server: $_"; Read-Host "Press Enter"; exit 1 }
$types = @{".html"="text/html; charset=utf-8";".css"="text/css";".js"="application/javascript";".json"="application/json";".svg"="image/svg+xml";".png"="image/png";".jpg"="image/jpeg";".jpeg"="image/jpeg";".webp"="image/webp";".ico"="image/x-icon";".woff2"="font/woff2";".pdf"="application/pdf"}
Start-Process "http://localhost:$port/"
Write-Host "CRSIS-47 preview running at http://localhost:$port/ - keep this window open. Press Ctrl+C to stop."
try {
 while ($listener.IsListening) {
  $context=$listener.GetContext()
  try {
   $relative=[Uri]::UnescapeDataString($context.Request.Url.AbsolutePath.TrimStart('/'))
   $file=[IO.Path]::GetFullPath((Join-Path $root $relative))
   if (-not ($file -eq $root -or $file.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase))) { $context.Response.StatusCode=403 }
   else {
    if ([IO.Directory]::Exists($file)) { $file=Join-Path $file "index.html" }
    if (-not [IO.File]::Exists($file)) { $context.Response.StatusCode=404 }
    else {
     $ext=[IO.Path]::GetExtension($file).ToLowerInvariant()
     $context.Response.ContentType=if ($types.ContainsKey($ext)) {$types[$ext]} else {"application/octet-stream"}
     $bytes=[IO.File]::ReadAllBytes($file)
     $context.Response.ContentLength64=$bytes.Length
     $context.Response.OutputStream.Write($bytes,0,$bytes.Length)
    }
   }
  } catch { $context.Response.StatusCode=500 }
  finally { $context.Response.Close() }
 }
} finally { $listener.Stop();$listener.Close() }
