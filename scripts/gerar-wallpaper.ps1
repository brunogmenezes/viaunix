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
Copy-Item $out "$root\packages\viaunix-branding\usr\share\backgrounds\viaunix\viaunix-wallpaper.png" -Force
Copy-Item "$root\branding\logo-jupiter.png" "$root\packages\viaunix-branding\usr\share\pixmaps\viaunix-logo.png" -Force
Write-Host "Gerado: $out"

# --- Derivados: GRUB (1920x1080) e logos redimensionados (Plymouth 400px, Calamares 256px/512px) ---
function Redimensionar($src, $dst, $nw, $nh) {
    $b = New-Object System.Drawing.Bitmap $nw, $nh
    $gr = [System.Drawing.Graphics]::FromImage($b)
    $gr.SmoothingMode = 'HighQuality'; $gr.InterpolationMode = 'HighQualityBicubic'
    $gr.DrawImage($src, 0, 0, $nw, $nh); $gr.Dispose()
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    $b.Save($dst, [System.Drawing.Imaging.ImageFormat]::Png); $b.Dispose()
    Write-Host "Gerado: $dst"
}
$inc = "$root\config\includes.chroot"
$brd = "$root\packages\viaunix-branding"
$wall = [System.Drawing.Image]::FromFile($out)
Redimensionar $wall "$brd\usr\share\backgrounds\viaunix\grub.png" 1920 1080
Redimensionar $logo "$brd\usr\share\plymouth\themes\viaunix\logo.png" 400 400
Redimensionar $logo "$inc\etc\calamares\branding\viaunix\logo.png" 256 256
Redimensionar $logo "$inc\etc\calamares\branding\viaunix\welcome.png" 512 512
$wall.Dispose()
