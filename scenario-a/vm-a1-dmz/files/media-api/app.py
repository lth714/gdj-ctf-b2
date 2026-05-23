"""Media Process API — IPTV content orchestration helper service."""
from flask import Flask, jsonify, request
import os, time, subprocess

app = Flask(__name__)
MEDIA_DIR = '/var/www/cms/uploads'


@app.route('/status')
def media_status():
    """Media service health status — storage and service info."""
    files = []
    if os.path.isdir(MEDIA_DIR):
        for f in os.listdir(MEDIA_DIR):
            p = os.path.join(MEDIA_DIR, f)
            if os.path.isfile(p):
                files.append({
                    'name': f,
                    'size': os.path.getsize(p),
                    'url': '/uploads/' + f,
                })
    return jsonify({
        'service': 'media-api',
        'status': 'running',
        'storage': MEDIA_DIR,
        'media_count': len(files),
    })


@app.route('/sync/status')
def sync_status():
    """Publish sync status — check last synchronization."""
    return jsonify({
        'service': 'iptv-publish-sync',
        'status': 'idle',
        'last_sync': int(time.time()) - 3600,
        'sync_target': 'internal',
        'message': 'waiting for next sync cycle',
    })


@app.route('/cover/resize')
def cover_resize():
    """Channel cover image resize proxy."""
    img = request.args.get('src', '')
    w = request.args.get('w', '320')
    h = request.args.get('h', '240')
    return jsonify({
        'action': 'resize_cover',
        'source': img,
        'target_size': '%sx%s' % (w, h),
        'status': 'ok',
        'processed': '/uploads/resized/' + os.path.basename(img),
    })


@app.route('/epg/import')
def epg_import():
    """EPG program guide import trigger."""
    provider = request.args.get('provider', 'default')
    return jsonify({
        'action': 'epg_import',
        'status': 'scheduled',
        'provider': provider,
        'message': 'EPG import job queued, will fetch from upstream provider',
    })


@app.route('/debug')
def debug_info():
    """Internal service debug (restricted to localhost)."""
    if request.remote_addr != '127.0.0.1':
        return jsonify({'error': 'access denied'}), 403
    return jsonify({
        'service': 'media-api-debug',
        'php_version': os.popen('php -v 2>/dev/null | head -1').read().strip(),
        'disk_usage': os.popen('df -h / | tail -1').read().strip(),
    })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
