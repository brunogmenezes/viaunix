# Gera o papel de parede padrão do ViaUnix (3840x2160) a partir do logo.
# Uso (Windows): powershell -File scripts\gerar-wallpaper.ps1
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$logo = [System.Drawing.Image]::FromFile("$root\branding\logo-jupiter.png")
$w = 3840; $h = 2160
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'HighQuality'; $g.InterpolationMode = 'HighQualityBicubic'
$rect = New-Object System.Drawing.Rectangle 0, 0, $w, $h
$c1 = [System.Drawing.Color]::FromArgb(255, 14, 40, 78)
$c2 = [System.Drawing.Color]::FromArgb(255, 5, 12, 26)
$br = New-Object System.Drawing.Drawing2D.LinearGradientBrush $rect, $c1, $c2, 60.0
$g.FillRectangle($br, $rect)
$size = [int]($h * 0.58)
$x = [int](($w - $size) / 2); $y = [int](($h - $size) / 2)
$g.DrawImage($logo, $x, $y, $size, $size)
$g.Dispose()
$out = "$root\branding\wallpaper\viaunix-wallpaper.png"
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
Copy-Item $out "$root\config\includes.chroot\usr\share\backgrounds\viaunix\viaunix-wallpaper.png" -Force
Write-Host "Gerado: $out"
