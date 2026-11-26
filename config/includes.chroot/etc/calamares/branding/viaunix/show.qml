import QtQuick 2.0
import calamares.slideshow 1.0

Presentation {
    id: presentation

    function nextSlide() { presentation.goToNextSlide() }
    Timer { interval: 6000; running: true; repeat: true; onTriggered: nextSlide() }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0e284e" }
        Text {
            anchors.centerIn: parent
            width: parent.width - 40
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "white"; font.pixelSize: 20
            text: "Bem-vindo ao ViaUnix\nUm sistema estável para o seu trabalho."
        }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#0e284e" }
        Text {
            anchors.centerIn: parent
            width: parent.width - 40
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "white"; font.pixelSize: 20
            text: "LibreOffice completo, OpenVPN e firewall\njá instalados e configurados."
        }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#0e284e" }
        Text {
            anchors.centerIn: parent
            width: parent.width - 40
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "white"; font.pixelSize: 20
            text: "Segurança em primeiro lugar.\nO sistema está sendo instalado..."
        }
    }
}
