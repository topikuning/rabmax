// BOQ Generator — ExtJS 4.2.1 (GPL) single-page app, served same-origin oleh FastAPI.
// Komponen core saja (grid + bufferedrenderer + rowediting) agar tahan tanpa ext-cmd.

// --- Penangkap error global: tampilkan ke layar, jangan biarkan halaman blank ---
window.__boqError = function (msg, stack) {
    try {
        var d = document.getElementById('boq-error');
        if (!d) {
            d = document.createElement('div');
            d.id = 'boq-error';
            d.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:999999;background:#c0272d;' +
                'color:#fff;font:12px/1.5 monospace;padding:12px;white-space:pre-wrap;max-height:60%;overflow:auto';
            (document.body || document.documentElement).appendChild(d);
        }
        d.textContent = 'BOQ ERROR: ' + msg + (stack ? '\n\n' + stack : '');
    } catch (e) { /* noop */ }
};
window.onerror = function (msg, src, line, col, err) {
    window.__boqError(msg + ' (' + src + ':' + line + ':' + col + ')', err && err.stack);
    return false;
};

if (typeof Ext === 'undefined') {
    window.__boqError('ExtJS gagal dimuat dari CDN. Cek URL di index.html / koneksi / pemblokir.');
    throw new Error('ExtJS not loaded');
}

Ext.ns('BOQ');

BOQ.token = {
    get: function () { return localStorage.getItem('boq_token'); },
    set: function (t) { localStorage.setItem('boq_token', t); },
    clear: function () { localStorage.removeItem('boq_token'); }
};

BOQ.applyAuth = function () {
    var t = BOQ.token.get();
    if (t) { Ext.Ajax.setDefaultHeaders({ Authorization: 'Bearer ' + t }); }
};

BOQ.notify = function (msg, ok) {
    var w = Ext.create('Ext.window.Window', {
        header: false, bodyPadding: 12, width: 320, closable: false,
        bodyStyle: 'background:' + (ok === false ? '#c0272d' : '#2e5d9e') + ';color:#fff;border:0',
        html: Ext.util.Format.htmlEncode(msg), shadow: true
    });
    w.show();
    w.alignTo(Ext.getBody(), 't-t', [0, 10]);
    Ext.defer(function () { w.close(); }, 3000);
};

BOQ.rupiah = function (v) {
    if (v === null || v === undefined || v === '') { return '-'; }
    return 'Rp ' + Ext.util.Format.number(v, '0,000');
};

// ---- 401 global → kembali ke login ----
Ext.Ajax.on('requestexception', function (conn, resp) {
    if (resp && resp.status === 401) { BOQ.token.clear(); BOQ.showLogin(); }
});

// ===================== LOGIN =====================
BOQ.showLogin = function () {
    if (BOQ.viewport) { BOQ.viewport.destroy(); BOQ.viewport = null; }
    if (BOQ.loginWin) { return; }

    var form = Ext.create('Ext.form.Panel', {
        bodyPadding: 16, border: false,
        defaults: { anchor: '100%', allowBlank: false, labelWidth: 90 },
        items: [
            { xtype: 'textfield', name: 'email', fieldLabel: 'Email', vtype: 'email' },
            { xtype: 'textfield', name: 'password', fieldLabel: 'Password', inputType: 'password' }
        ]
    });

    var doLogin = function () {
        var v = form.getValues();
        if (!v.email || !v.password) { BOQ.notify('Isi email & password', false); return; }
        BOQ.loginWin.setLoading(true);
        Ext.Ajax.request({
            url: '/api/auth/login', method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            params: { username: v.email, password: v.password },
            success: function (r) {
                var d = Ext.decode(r.responseText);
                BOQ.token.set(d.access_token); BOQ.applyAuth();
                BOQ.loginWin.close(); BOQ.loginWin = null; BOQ.showApp();
            },
            failure: function () { BOQ.loginWin.setLoading(false); BOQ.notify('Email atau password salah', false); }
        });
    };

    var doRegister = function () {
        var v = form.getValues();
        if (!v.email || !v.password) { BOQ.notify('Isi email & password (min 8)', false); return; }
        BOQ.loginWin.setLoading(true);
        Ext.Ajax.request({
            url: '/api/auth/register', method: 'POST', jsonData: { email: v.email, password: v.password },
            success: function () { BOQ.loginWin.setLoading(false); doLogin(); },
            failure: function (r) { BOQ.loginWin.setLoading(false); BOQ.notify('Gagal daftar: ' + r.responseText, false); }
        });
    };

    BOQ.loginWin = Ext.create('Ext.window.Window', {
        title: 'BOQ Generator — Masuk', width: 380, closable: false, resizable: false,
        layout: 'fit', items: [form],
        buttons: [
            { text: 'Daftar', handler: doRegister },
            { text: 'Masuk', type: 'submit', handler: doLogin }
        ]
    });
    form.on('afterrender', function () {
        Ext.EventManager.on(document, 'keypress', function (e) {
            if (e.getKey() === e.ENTER && BOQ.loginWin) { doLogin(); }
        });
    });
    BOQ.loginWin.show();
};

// ===================== STORES =====================
BOQ.ahspStore = function () {
    if (!BOQ._ahsp) {
        BOQ._ahsp = Ext.create('Ext.data.Store', {
            storeId: 'ahsp',
            fields: ['id', 'kode', 'uraian', 'satuan', 'source', 'confidence_tier', 'work_group'],
            proxy: { type: 'ajax', url: '/api/ahsp?limit=8000', reader: { type: 'json', root: '' } },
            autoLoad: true
        });
    }
    return BOQ._ahsp;
};

// ===================== GRID: AHSP =====================
BOQ.ahspGrid = function () {
    var store = BOQ.ahspStore();
    var search = Ext.create('Ext.form.field.Text', {
        emptyText: 'Cari kode / uraian / work group…', width: 320, flex: 1,
        listeners: {
            change: { buffer: 250, fn: function (f, val) {
                store.clearFilter();
                if (val) {
                    var q = val.toLowerCase();
                    store.filterBy(function (rec) {
                        return (rec.get('kode') + ' ' + rec.get('uraian') + ' ' + (rec.get('work_group') || ''))
                            .toLowerCase().indexOf(q) !== -1;
                    });
                }
            }}
        }
    });
    return Ext.create('Ext.grid.Panel', {
        title: 'Katalog AHSP', store: store, border: false,
        plugins: [{ ptype: 'bufferedrenderer' }],
        columns: [
            { text: 'Kode', dataIndex: 'kode', width: 150 },
            { text: 'Uraian', dataIndex: 'uraian', flex: 1 },
            { text: 'Satuan', dataIndex: 'satuan', width: 80 },
            { text: 'Work Group', dataIndex: 'work_group', width: 120 },
            { text: 'Sumber', dataIndex: 'source', width: 150 },
            { text: 'Tier', dataIndex: 'confidence_tier', width: 110 }
        ],
        tbar: [search, '->', { xtype: 'button', text: 'Muat ulang', handler: function () { store.reload(); } },
            { xtype: 'tbtext', itemId: 'cnt' }],
        listeners: {
            afterrender: function (g) {
                var upd = function () { g.down('#cnt').setText(store.getCount() + ' item'); };
                store.on('datachanged', upd); store.on('load', upd); upd();
            }
        }
    });
};

// ===================== GRID: BAHAN & UPAH =====================
BOQ.bahanGrid = function () {
    var store = Ext.create('Ext.data.Store', {
        fields: ['id', 'nama', 'satuan', { name: 'harga', type: 'float' }, 'category', 'tier',
            { name: 'tkdn_factor', type: 'float' }, 'source_label', 'provinsi', 'tahun'],
        proxy: { type: 'ajax', url: '/api/bahan-upah?limit=8000', reader: { type: 'json', root: '' } },
        autoLoad: true
    });
    var search = Ext.create('Ext.form.field.Text', {
        emptyText: 'Cari nama material/upah…', flex: 1,
        listeners: { change: { buffer: 250, fn: function (f, val) {
            store.clearFilter();
            if (val) { var q = val.toLowerCase(); store.filterBy(function (r) { return r.get('nama').toLowerCase().indexOf(q) !== -1; }); }
        }}}
    });
    return Ext.create('Ext.grid.Panel', {
        title: 'Bahan & Upah', store: store, border: false,
        plugins: [{ ptype: 'bufferedrenderer' }],
        columns: [
            { text: 'Nama', dataIndex: 'nama', flex: 1 },
            { text: 'Satuan', dataIndex: 'satuan', width: 80 },
            { text: 'Harga', dataIndex: 'harga', width: 130, align: 'right', renderer: BOQ.rupiah },
            { text: 'Kategori', dataIndex: 'category', width: 90 },
            { text: 'Tier', dataIndex: 'tier', width: 60 },
            { text: 'TKDN', dataIndex: 'tkdn_factor', width: 70, renderer: function (v) { return v != null ? (v * 100).toFixed(0) + '%' : '-'; } },
            { text: 'Sumber', dataIndex: 'source_label', width: 200 },
            { text: 'Tahun', dataIndex: 'tahun', width: 70 }
        ],
        tbar: [search]
    });
};

// ===================== GRID: PROJECTS =====================
BOQ.projectsGrid = function () {
    var store = Ext.create('Ext.data.Store', {
        fields: ['id', 'name', 'lokasi', 'tahun_anggaran', { name: 'target_value', type: 'float' },
            'mode', 'status', 'created_at'],
        proxy: { type: 'ajax', url: '/api/projects', reader: { type: 'json', root: '' } },
        autoLoad: true
    });
    BOQ._projStore = store;

    var openSel = function (g) {
        var rec = g.getSelectionModel().getSelection()[0];
        if (rec) { BOQ.openWorkspace(rec.getData()); }
    };

    return Ext.create('Ext.grid.Panel', {
        title: 'Proyek', store: store, border: false,
        columns: [
            { text: 'Nama', dataIndex: 'name', flex: 1 },
            { text: 'Lokasi', dataIndex: 'lokasi', width: 180 },
            { text: 'Mode', dataIndex: 'mode', width: 130, renderer: function (v) { return v === 'generate' ? 'Generate BOQ' : 'Analisa Profit'; } },
            { text: 'Status', dataIndex: 'status', width: 140 },
            { text: 'Target', dataIndex: 'target_value', width: 140, align: 'right', renderer: BOQ.rupiah }
        ],
        tbar: [
            { text: 'Proyek Baru', iconCls: 'x-tbar-add', handler: BOQ.newProject },
            { text: 'Buka', handler: function (b) { openSel(b.up('grid')); } },
            '->', { text: 'Muat ulang', handler: function () { store.reload(); } }
        ],
        listeners: { itemdblclick: function (g, rec) { BOQ.openWorkspace(rec.getData()); } }
    });
};

BOQ.newProject = function () {
    var form = Ext.create('Ext.form.Panel', {
        bodyPadding: 14, border: false, defaults: { anchor: '100%', labelWidth: 110 },
        items: [
            { xtype: 'textfield', name: 'name', fieldLabel: 'Nama proyek', allowBlank: false },
            { xtype: 'textfield', name: 'lokasi', fieldLabel: 'Lokasi' },
            { xtype: 'numberfield', name: 'tahun_anggaran', fieldLabel: 'Tahun anggaran', value: 2026 },
            { xtype: 'numberfield', name: 'target_value', fieldLabel: 'Target nilai (Rp)', minValue: 0, hideTrigger: true },
            { xtype: 'combo', name: 'mode', fieldLabel: 'Mode', value: 'generate', editable: false,
              store: [['generate', 'Generate BOQ'], ['profit_analysis', 'Analisa Profit']] }
        ]
    });
    var win = Ext.create('Ext.window.Window', {
        title: 'Proyek Baru', width: 460, layout: 'fit', modal: true, items: [form],
        buttons: [{ text: 'Batal', handler: function () { win.close(); } },
            { text: 'Buat', handler: function () {
                if (!form.isValid()) { return; }
                win.setLoading(true);
                Ext.Ajax.request({
                    url: '/api/projects', method: 'POST', jsonData: form.getValues(),
                    success: function (r) { win.close(); BOQ._projStore.reload(); BOQ.openWorkspace(Ext.decode(r.responseText)); },
                    failure: function (r) { win.setLoading(false); BOQ.notify('Gagal: ' + r.responseText, false); }
                });
            }}]
    });
    win.show();
};

// ===================== WORKSPACE (per proyek) =====================
BOQ.openWorkspace = function (project) {
    var center = BOQ.viewport.down('#center');
    var id = 'ws-' + project.id;
    var existing = center.down('#' + id);
    if (existing) { center.getLayout().setActiveItem(existing); return; }

    var ahsp = BOQ.ahspStore();
    var itemStore = Ext.create('Ext.data.Store', {
        fields: ['paket_item_id', 'sheet_name', 'uraian', 'satuan', { name: 'volume', type: 'float' },
            'match_id', 'match_type', { name: 'ahsp_id', type: 'int', useNull: true },
            { name: 'lumpsum_price', type: 'float', useNull: true },
            { name: 'final_hsp', type: 'float', useNull: true },
            { name: 'confidence', type: 'float' }, { name: 'reviewed_by_user', type: 'bool' }]
    });

    var reload = function () {
        Ext.Ajax.request({ url: '/api/matches/' + project.id + '/items', success: function (r1) {
            var items = Ext.decode(r1.responseText);
            Ext.Ajax.request({ url: '/api/matches/' + project.id, success: function (r2) {
                var matches = Ext.decode(r2.responseText), byItem = {};
                Ext.each(matches, function (m) { byItem[m.paket_item_id] = m; });
                var rows = Ext.Array.map(items, function (it) {
                    var m = byItem[it.id] || {};
                    return {
                        paket_item_id: it.id, sheet_name: it.sheet_name, uraian: it.uraian,
                        satuan: it.satuan, volume: it.volume,
                        match_id: m.id, match_type: m.match_type, ahsp_id: m.ahsp_id,
                        lumpsum_price: m.lumpsum_price, final_hsp: m.final_hsp,
                        confidence: m.confidence, reviewed_by_user: m.reviewed_by_user
                    };
                });
                itemStore.loadData(rows);
            }});
        }});
    };

    var rowEdit = Ext.create('Ext.grid.plugin.RowEditing', { clicksToEdit: 2, autoCancel: false });
    rowEdit.on('edit', function (editor, ctx) {
        var rec = ctx.record;
        if (!rec.get('match_id')) { BOQ.notify('Item ini belum punya match (jalankan parse/match).', false); rec.reject(); return; }
        var body = {
            match_type: rec.get('match_type'),
            ahsp_id: rec.get('ahsp_id') || null,
            lumpsum_price: rec.get('lumpsum_price') || null
        };
        Ext.Ajax.request({
            url: '/api/matches/' + rec.get('match_id'), method: 'PATCH', jsonData: body,
            success: function () { rec.set('reviewed_by_user', true); rec.set('confidence', 1); rec.commit(); BOQ.notify('Match disimpan'); },
            failure: function (r) { rec.reject(); BOQ.notify('Gagal simpan: ' + r.responseText, false); }
        });
    });

    var isGen = project.mode === 'generate';

    var grid = Ext.create('Ext.grid.Panel', {
        store: itemStore, border: false, flex: 1, plugins: [{ ptype: 'bufferedrenderer' }, rowEdit],
        columns: [
            { text: 'Sheet', dataIndex: 'sheet_name', width: 120 },
            { text: 'Uraian', dataIndex: 'uraian', flex: 1 },
            { text: 'Sat', dataIndex: 'satuan', width: 60 },
            { text: 'Volume', dataIndex: 'volume', width: 90, align: 'right' },
            { text: 'Tipe', dataIndex: 'match_type', width: 110, editor: {
                xtype: 'combo', editable: false, store: ['ahsp', 'lumpsum', 'unresolved'] } },
            { text: 'AHSP', dataIndex: 'ahsp_id', width: 150,
              renderer: function (v) { var rr = v ? ahsp.getById(v) : null; return rr ? rr.get('kode') : (v || ''); },
              editor: { xtype: 'combo', store: ahsp, valueField: 'id', displayField: 'kode',
                  queryMode: 'local', typeAhead: true, forceSelection: false, minChars: 1,
                  listConfig: { getInnerTpl: function () { return '{kode} — {uraian}'; } } } },
            { text: 'Lumpsum', dataIndex: 'lumpsum_price', width: 120, align: 'right', renderer: BOQ.rupiah,
              editor: { xtype: 'numberfield', minValue: 0, hideTrigger: true, allowBlank: true } },
            { text: 'HSP final', dataIndex: 'final_hsp', width: 130, align: 'right', renderer: BOQ.rupiah },
            { text: 'Conf', dataIndex: 'confidence', width: 60, renderer: function (v) { return v != null ? (v * 100).toFixed(0) + '%' : ''; } },
            { text: 'Review', dataIndex: 'reviewed_by_user', width: 70, renderer: function (v) { return v ? '✓' : ''; } }
        ],
        tbar: [{ xtype: 'tbtext', html: '<b>Item & Match</b> — klik 2x baris untuk override' },
            '->', { text: 'Muat ulang', handler: reload }]
    });

    // pipeline toolbar
    var act = function (key, url, method) {
        var p = wsPanel; p.setLoading(true);
        Ext.Ajax.request({ url: url, method: method || 'POST', success: function (r) {
            p.setLoading(false); BOQ.notify(key + ' selesai'); reload(); BOQ._projStore && BOQ._projStore.reload();
            if (key === 'Generate') {
                var d = Ext.decode(r.responseText);
                if (d.download_url) { window.open(d.download_url, '_blank'); }
            }
        }, failure: function (r) { p.setLoading(false); BOQ.notify(key + ' gagal: ' + r.responseText, false); } });
    };

    var uploadBtn = {
        text: 'Upload RAB', iconCls: 'x-tbar-loading', handler: function () {
            var inp = document.createElement('input');
            inp.type = 'file'; inp.accept = '.xlsx,.xlsm';
            inp.onchange = function () {
                var f = inp.files[0]; if (!f) { return; }
                var fd = new FormData(); fd.append('file', f); fd.append('mode', project.mode);
                wsPanel.setLoading(true);
                fetch('/api/upload/' + project.id, { method: 'POST',
                    headers: { Authorization: 'Bearer ' + BOQ.token.get() }, body: fd })
                    .then(function (res) { return res.ok ? res.json() : res.text().then(function (t) { throw new Error(t); }); })
                    .then(function (s) { wsPanel.setLoading(false); BOQ.notify('Parse: ' + s.items_total + ' item'); reload(); })
                    .catch(function (e) { wsPanel.setLoading(false); BOQ.notify('Upload gagal: ' + e.message, false); });
            };
            inp.click();
        }
    };

    var pipeline = isGen ? [
        uploadBtn, '-',
        { text: '2. Match', handler: function () { act('Match', '/api/matches/' + project.id + '/run'); } },
        { text: '3. Harga + Kalibrasi', handler: function () { act('Pricing', '/api/projects/' + project.id + '/price'); } },
        { text: '4. Generate', iconCls: 'x-tbar-page', handler: function () { act('Generate', '/api/projects/' + project.id + '/generate'); } }
    ] : [
        uploadBtn, '-',
        { text: 'Jalankan Analisa Profit', handler: function () { act('Profit', '/api/profit/' + project.id + '/run'); } }
    ];

    var wsPanel = Ext.create('Ext.panel.Panel', {
        itemId: id, title: project.name + '  (' + (isGen ? 'Generate' : 'Profit') + ')',
        closable: true, layout: { type: 'vbox', align: 'stretch' }, border: false,
        tbar: pipeline, items: [grid]
    });
    center.add(wsPanel);
    center.getLayout().setActiveItem(wsPanel);
    reload();
};

// ===================== ADMIN =====================
BOQ.adminPanel = function () {
    var statTpl = new Ext.XTemplate('<div style="padding:6px 0">AHSP: <b>{ahsp_count}</b> &nbsp; | &nbsp; Bahan & Upah: <b>{bahan_upah_count}</b></div>');
    var statBox = Ext.create('Ext.Component', { html: 'Memuat…' });
    var loadStats = function () {
        Ext.Ajax.request({ url: '/api/admin/stats',
            success: function (r) { statBox.update(statTpl.apply(Ext.decode(r.responseText))); },
            failure: function () { statBox.update('<i>Butuh hak superuser.</i>'); } });
    };
    var seedBtn = { xtype: 'button', text: 'Seed AHSP bawaan (SE DJBK 47/2026)', handler: function (b) {
        b.setDisabled(true); b.setText('Memproses…');
        Ext.Ajax.request({ url: '/api/admin/seed/ahsp/bundled', method: 'POST',
            success: function (r) { var d = Ext.decode(r.responseText); BOQ.notify('Seed: +' + d.created + ' baru'); b.setDisabled(false); b.setText('Seed AHSP bawaan (SE DJBK 47/2026)'); loadStats(); BOQ._ahsp && BOQ._ahsp.reload(); },
            failure: function (r) { BOQ.notify('Gagal: ' + r.responseText, false); b.setDisabled(false); b.setText('Seed AHSP bawaan (SE DJBK 47/2026)'); } });
    }};
    var uploadSeed = function (kind, label) {
        return { xtype: 'button', text: label, handler: function () {
            var inp = document.createElement('input'); inp.type = 'file'; inp.accept = '.json,.jsonl,.gz';
            inp.onchange = function () {
                var f = inp.files[0]; if (!f) { return; }
                var fd = new FormData(); fd.append('file', f);
                Ext.getBody().mask('Upload & seed…');
                fetch('/api/admin/seed/' + kind, { method: 'POST', headers: { Authorization: 'Bearer ' + BOQ.token.get() }, body: fd })
                    .then(function (res) { return res.ok ? res.json() : res.text().then(function (t) { throw new Error(t); }); })
                    .then(function (d) { Ext.getBody().unmask(); BOQ.notify('Seed OK: ' + JSON.stringify(d).slice(0, 120)); loadStats(); })
                    .catch(function (e) { Ext.getBody().unmask(); BOQ.notify('Gagal: ' + e.message, false); });
            };
            inp.click();
        }};
    };
    loadStats();
    return Ext.create('Ext.panel.Panel', {
        title: 'Admin — Data Master', bodyPadding: 16, border: false, autoScroll: true,
        items: [statBox, { xtype: 'box', height: 12 }, seedBtn, { xtype: 'box', height: 10 },
            uploadSeed('ahsp', 'Upload AHSP (JSON/JSONL/.gz)'), { xtype: 'box', height: 8 },
            uploadSeed('bahan-upah', 'Upload Harga Bahan & Upah'), { xtype: 'box', height: 16 },
            { xtype: 'button', text: 'Refresh statistik', handler: loadStats }]
    });
};

// ===================== APP SHELL =====================
BOQ.showApp = function () {
  try {
    var center = Ext.create('Ext.panel.Panel', { itemId: 'center', region: 'center', layout: 'card', border: false,
        items: [BOQ.projectsGrid()] });

    var nav = function (text, builder) {
        var key = 'static-' + text.replace(/[^a-z0-9]/gi, '');  // hindari spasi/& di id
        return { xtype: 'button', text: text, textAlign: 'left', margin: '2 6', scale: 'medium',
            handler: function () {
                try {
                    var c = center.down('#' + key);
                    if (!c) { c = builder(); c.itemId = key; center.add(c); }
                    center.getLayout().setActiveItem(c);
                } catch (e) { window.__boqError(text + ' gagal: ' + e.message, e.stack); }
            }};
    };

    BOQ.viewport = Ext.create('Ext.container.Viewport', {
        layout: 'border',
        items: [
            { region: 'north', height: 48, bodyStyle: 'background:#2e5d9e', border: false,
              layout: { type: 'hbox', align: 'middle' }, padding: '0 12',
              items: [{ xtype: 'box', html: '<span class="boq-header-title">BOQ Generator</span>' }, { xtype: 'box', flex: 1 },
                  { xtype: 'button', text: 'Keluar', handler: function () { BOQ.token.clear(); BOQ.showLogin(); } }] },
            { region: 'west', width: 200, title: 'Menu', collapsible: true, split: true, bodyPadding: 6,
              layout: { type: 'vbox', align: 'stretch' },
              items: [
                  { xtype: 'button', text: 'Proyek', textAlign: 'left', margin: '2 6', scale: 'medium',
                    handler: function () { var g = center.down('grid[title=Proyek]') || BOQ.projectsGrid(); center.getLayout().setActiveItem(center.items.first()); } },
                  nav('AHSP', BOQ.ahspGrid),
                  nav('Bahan & Upah', BOQ.bahanGrid),
                  nav('Admin', BOQ.adminPanel)
              ] },
            center
        ]
    });
  } catch (e) { window.__boqError('showApp gagal: ' + e.message, e.stack); }
};

// ===================== BOOT =====================
Ext.onReady(function () {
    try {
        Ext.tip.QuickTipManager.init();
        BOQ.applyAuth();
        if (BOQ.token.get()) { BOQ.showApp(); } else { BOQ.showLogin(); }
    } catch (e) {
        window.__boqError('Boot gagal: ' + e.message, e.stack);
    }
});
