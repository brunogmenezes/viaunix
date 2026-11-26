import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';

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

class VpnLoginDialog extends ModalDialog.ModalDialog {
    constructor(onSubmit) {
        super({styleClass: 'viaunix-vpn-dialog'});
        this._onSubmit = onSubmit;

        const box = new St.BoxLayout({vertical: true, style: 'spacing: 10px; min-width: 300px;'});
        this.contentLayout.add_child(box);

        box.add_child(new St.Label({
            text: 'Conectar ViaUnix VPN',
            style: 'font-weight: bold; font-size: 15px;',
        }));
        box.add_child(new St.Label({
            text: 'Informe seu usuário e senha corporativos:',
        }));

        this._userEntry = new St.Entry({
            hint_text: 'Usuário',
            can_focus: true,
        });
        this._passEntry = new St.PasswordEntry({
            hint_text: 'Senha',
            can_focus: true,
        });

        box.add_child(this._userEntry);
        box.add_child(this._passEntry);

        this._passEntry.clutter_text.connect('activate', () => this._submit());
        this._userEntry.clutter_text.connect('activate', () => this._passEntry.grab_key_focus());

        this.setButtons([
            {
                label: 'Cancelar',
                action: () => this.close(),
                key: Clutter.KEY_Escape,
            },
            {
                label: 'Conectar',
                action: () => this._submit(),
                default: true,
            },
        ]);
    }

    open() {
        super.open();
        this._userEntry.grab_key_focus();
    }

    _submit() {
        const user = this._userEntry.get_text().trim();
        const pass = this._passEntry.get_text();
        if (!user || !pass)
            return;
        this.close();
        this._onSubmit(user, pass);
    }
}

export default class ViaUnixVpnExtension extends Extension {
    enable() {
        this._indicator = new PanelMenu.Button(0.0, 'ViaUnix VPN', false);
        this._label = new St.Label({
            text: 'VPN: ...',
            y_align: Clutter.ActorAlign.CENTER,
            style: 'padding: 0 6px; font-weight: bold;',
        });
        this._indicator.add_child(this._label);

        this._statusItem = new PopupMenu.PopupMenuItem('Verificando VPN...', {reactive: false});
        this._connectItem = new PopupMenu.PopupMenuItem('Conectar VPN...');
        this._disconnectItem = new PopupMenu.PopupMenuItem('Desconectar VPN');

        this._connectItem.connect('activate', () => this._openConnectDialog());
        this._disconnectItem.connect('activate', () => this._disconnect());

        this._indicator.menu.addMenuItem(this._statusItem);
        this._indicator.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._indicator.menu.addMenuItem(this._connectItem);
        this._indicator.menu.addMenuItem(this._disconnectItem);

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
            this._connectItem.visible = false;
            this._disconnectItem.visible = true;
            return;
        }

        const stRes = await runCommandAsync(['/bin/systemctl', 'is-active', 'openvpn-client@viaunix.service']);
        if (!this._indicator)
            return;

        const st = stRes.stdout.trim();
        if (st === 'active' || st === 'activating') {
            this._label.set_text('◐ VPN...');
            this._statusItem.label.set_text('Conectando na VPN...');
            this._connectItem.visible = false;
            this._disconnectItem.visible = true;
        } else {
            this._label.set_text('○ VPN');
            this._statusItem.label.set_text('VPN Desconectada');
            this._connectItem.visible = true;
            this._disconnectItem.visible = false;
        }
    }

    _openConnectDialog() {
        const dlg = new VpnLoginDialog(async (user, pass) => {
            this._label.set_text('◐ VPN...');
            await runCommandAsync(
                ['/usr/bin/sudo', '-n', '/usr/sbin/viaunix-vpn-connect'],
                `${user}\n${pass}\n`
            );
            this._refresh();
        });
        dlg.open();
    }

    async _disconnect() {
        await runCommandAsync(['/usr/bin/sudo', '-n', '/usr/sbin/viaunix-vpn-disconnect']);
        this._refresh();
    }
}
