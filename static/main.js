$(function() {
    // Carregar usuários
    function loadUsers() {
        $.get('/api/users', function(users) {
            let html = '';
            users.forEach(u => {
                html += `<li class="list-group-item">${u.user}</li>`;
            });
            $('#users-list').html(html);
        });
    }
    loadUsers();
    // Adicionar usuário
    $('#add-user-form').submit(function(e) {
        e.preventDefault();
        $.ajax({
            url: '/api/users',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ user: $('#user').val(), password: $('#password').val() }),
            success: function() {
                $('#user').val('');
                $('#password').val('');
                loadUsers();
            }
        });
    });
    // Upload M3U
    let filmes = [];
    let m3uPath = '';
    $('#upload-form').submit(function(e) {
        e.preventDefault();
        let file = $('#m3u-file')[0].files[0];
        if (!file) return;
        let formData = new FormData();
        formData.append('file', file);
        $.ajax({
            url: '/api/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(res) {
                filmes = res.filmes;
                m3uPath = res.m3u_path;
                let html = '<ul>';
                filmes.forEach(f => {
                    html += `<li>${f.title}</li>`;
                });
                html += '</ul>';
                $('#filmes-list').html(html);
                if (filmes.length > 0) {
                    $('#download-btn').removeClass('d-none');
                }
            }
        });
    });
    // Processar texto colado
    $('#paste-form').submit(function(e) {
        e.preventDefault();
        let text = $('#m3u-text').val();
        if (!text.trim()) return;
        $.ajax({
            url: '/api/paste',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ text }),
            success: function(res) {
                filmes = res.filmes;
                m3uPath = res.m3u_path;
                let html = '<ul>';
                filmes.forEach(f => {
                    html += `<li>${f.title}</li>`;
                });
                html += '</ul>';
                $('#filmes-list').html(html);
                if (filmes.length > 0) {
                    $('#download-btn').removeClass('d-none');
                }
            }
        });
    });
    // Iniciar downloads
    let keys = [];
    $('#download-btn').click(function() {
        $('#progress-section').html('Iniciando downloads...');
        let downloadDir = $('#download-dir').val() || 'downloads';
        $.ajax({
            url: '/api/download',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ m3u_path: m3uPath, download_dir: downloadDir }),
            success: function(res) {
                keys = res.keys;
                showProgress();
                pollStatus();
            }
        });
    });
    // Progresso
    function showProgress(statuses) {
        let html = '';
        (keys || []).forEach(k => {
            let st = statuses ? statuses[k.key] : (k.skipped ? 'skipped' : 'downloading');
            let bar = '';
            if (st === 'done') bar = '<div class="progress-bar bg-success" style="width:100%">Concluído</div>';
            else if (st === 'skipped') bar = '<div class="progress-bar bg-warning" style="width:100%">Já baixado</div>';
            else if (st.startsWith('error')) bar = `<div class="progress-bar bg-danger" style="width:100%">Erro</div>`;
            else bar = '<div class="progress-bar progress-bar-striped progress-bar-animated" style="width:100%">Baixando...</div>';
            html += `<div><b>${k.title}</b><div class="progress">${bar}</div></div>`;
        });
        $('#progress-section').html(html);
    }
    function pollStatus() {
        if (!keys.length) return;
        $.ajax({
            url: '/api/status',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ keys }),
            success: function(statuses) {
                showProgress(statuses);
                let allDone = Object.values(statuses).every(st => st === 'done' || st.startsWith('error'));
                if (!allDone) setTimeout(pollStatus, 1500);
            }
        });
    }
});
