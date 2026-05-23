"""Pack php-iptv-proxy source into tar.gz for deployment."""
import tarfile
import os

src = 'E:/vibecoding/gdj_ctf/q1/php-iptv-proxy-master'
out = 'E:/vibecoding/gdj_ctf/iptv-proxy-deploy.tar.gz'

exclude = {
    '.git', '.gitignore', '.gitattributes', '.dockerignore',
    'docker', 'Dockerfile', 'docker-compose.yml', 'docker-creat.sh',
    'process.md', 'LICENSE.txt', '404.html', '.htaccess',
}

with tarfile.open(out, 'w:gz') as tar:
    src_dir = os.path.dirname(src)
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in exclude]
        for f in files:
            if f in exclude:
                continue
            full = os.path.join(root, f)
            arcname = os.path.relpath(full, src_dir).replace('\\', '/')
            tar.add(full, arcname=arcname)

size_mb = os.path.getsize(out) / 1024 / 1024
print(f'Packed: {out} ({size_mb:.1f} MB)')
