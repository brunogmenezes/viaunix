import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

function runCommandAsync(argv, stdinText = null) {
    return new Promise((resolve) => {
        try {
            const flags = stdinText !== null
                ? (Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
                : (Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            const proc = Gio.Subprocess.new(argv, flags);
            proc.communicate_utf8_async(stdinText, null, (p, res) => {
                try {
                    const [, stdout, stderr] = p.communicate_utf8_finish(res);
                    resolve({ok: p.get_successful(), stdout: stdout || '', stderr: stderr || ''});
                } catch (_e) {
                    resolve({ok: false, stdout: '', stderr: ''});
                }
            });
        } catch (_e) {
            resolve({ok: false, stdout: '', stderr: ''});
        }
    });
}

export default class ViaUnixVpnExtension extends Extension {
    enable() {
        this._indicator = new PanelMenu.Button(0.0, 'ViaUnix VPN', false);
        this._label = new St.Label({
            text: '○ VPN',
            y_align: Clutter.ActorAlign.CENTER,
            style: 'padding: 0 6px; font-weight: bold;',
        });
        this._indicator.add_child(this._label);

        this._statusItem = new PopupMenu.PopupMenuItem('Verificando VPN...', {reactive: false});
        this._indicator.menu.addMenuItem(this._statusItem);
        this._indicator.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Formulario direto dentro do menu (evita conflito de ModalDialog no GDM e tela de bloqueio)
        this._formItem = new PopupMenu.PopupBaseMenuItem({reactive: false, can_focus: false});
        const formBox = new St.BoxLayout({
            vertical: true,
            style: 'spacing: 8px; min-width: 240px; padding: 4px 0;',
        });

        this._userEntry = new St.Entry({
            hint_text: 'Usuário',
            can_focus: true,
            style: 'min-width: 230px;',
        });
        this._passEntry = new St.PasswordEntry({
            hint_text: 'Senha',
            can_focus: true,
            style: 'min-width: 230px;',
        });
        this._connectBtn = new St.Button({
            label: 'Conectar VPN',
            can_focus: true,
            style: 'background-color: #ff9f1a; color: #081529; font-weight: bold; border-radius: 6px; padding: 6px 12px;',
        });
        this._feedbackLbl = new St.Label({
            text: '',
            style: 'color: #ff7675; font-size: 11px;',
        });
        this._feedbackLbl.visible = false;

        this._userEntry.clutter_text.connect('activate', () => this._passEntry.grab_key_focus());
        this._passEntry.clutter_text.connect('activate', () => this._connect());
        this._connectBtn.connect('clicked', () => this._connect());

        formBox.add_child(this._userEntry);
        formBox.add_child(this._passEntry);
        formBox.add_child(this._connectBtn);
        formBox.add_child(this._feedbackLbl);
        this._formItem.add_child(formBox);
        this._indicator.menu.addMenuItem(this._formItem);

        this._disconnectItem = new PopupMenu.PopupMenuItem('Desconectar VPN');
        this._disconnectItem.connect('activate', () => this._disconnect());
        this._indicator.menu.addMenuItem(this._disconnectItem);

        this._indicator.menu.connect('open-state-changed', (_menu, isOpen) => {
            if (isOpen && this._formItem.visible) {
                GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                    this._userEntry?.grab_key_focus();
                    return GLib.SOURCE_REMOVE;
                });
            }
        });

        Main.panel.addToStatusArea(this.uuid, this._indicator, 1, 'right');

        this._refresh();
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 4, () => {
            this._refresh();
            return GLib.SOURCE_CONTINUE;
        });
    }

    disable() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = null;
        }
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }

    async _refresh() {
        const ipRes = await runCommandAsync(['/usr/sbin/ip', '-4', '-o', 'addr', 'show', 'dev', 'tun0']);
        if (!this._indicator)
            return;

        const m = ipRes.ok ? ipRes.stdout.match(/inet\s+([0-9.]+)/) : null;
        if (m) {
            this._label.set_text(`● VPN (${m[1]})`);
            this._statusItem.label.set_text(`Conectada — IP ${m[1]}`);
            this._formItem.visible = false;
            this._disconnectItem.visible = true;
            this._feedbackLbl.visible = false;
            return;
        }

        const stRes = await runCommandAsync(['/bin/systemctl', 'is-active', 'openvpn-client@viaunix.service']);
        if (!this._indicator)
            return;

        const st = stRes.stdout.trim();
        if (st === 'active' || st === 'activating') {
            this._label.set_text('◐ VPN...');
            this._statusItem.label.set_text('Conectando na VPN...');
            this._formItem.visible = false;
            this._disconnectItem.visible = true;
        } else {
            this._label.set_text('○ VPN');
            this._statusItem.label.set_text('VPN Desconectada');
            this._formItem.visible = true;
            this._disconnectItem.visible = false;
        }
    }

    async _connect() {
        const user = this._userEntry.get_text().trim();
        const pass = this._passEntry.get_text();
        if (!user || !pass) {
            this._feedbackLbl.set_text('Informe usuário e senha.');
            this._feedbackLbl.visible = true;
            return;
        }

        this._feedbackLbl.visible = false;
        this._passEntry.set_text('');
        this._label.set_text('◐ VPN...');
        this._statusItem.label.set_text('Conectando na VPN...');

        const res = await runCommandAsync(
            ['/usr/bin/sudo', '-n', '/usr/sbin/viaunix-vpn-connect'],
            `${user}\n${pass}\n`
        );
        if (!res.ok) {
            this._feedbackLbl.set_text('Erro ao iniciar VPN.');
            this._feedbackLbl.visible = true;
        } else {
            this._indicator.menu.close();
        }
        this._refresh();
    }

    async _disconnect() {
        await runCommandAsync(['/usr/bin/sudo', '-n', '/usr/sbin/viaunix-vpn-disconnect']);
        this._refresh();
    }
}
