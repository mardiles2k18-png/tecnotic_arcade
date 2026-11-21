import QtQuick 2.7

FocusScope {
    id: root
    focus: true
    readonly property real unit: Math.min(width / 1280, height / 720)
    readonly property color accent: "#00d4ef"
    property int systemIndex: 0
    readonly property var collection: api.collections.count > systemIndex ? api.collections.get(systemIndex) : null
    readonly property var game: collection && games.currentIndex >= 0 && games.currentIndex < collection.games.count ? collection.games.get(games.currentIndex) : null
    readonly property string systemKey: collection ? collection.shortName : ""
    readonly property bool knownSystem: ["ps2", "ps3", "ps4", "switch", "xbox360", "fbneo", "mame", "windows"].indexOf(systemKey) >= 0
    function changeSystem(step) {
        if (!api.collections.count) return;
        systemIndex = (systemIndex + step + api.collections.count) % api.collections.count;
        games.currentIndex = 0;
    }
    function play() { if (game) game.launch(); }
    Keys.onPressed: {
        if (event.key === Qt.Key_Left || api.keys.isPrevPage(event)) { changeSystem(-1); event.accepted = true; }
        else if (event.key === Qt.Key_Right || api.keys.isNextPage(event)) { changeSystem(1); event.accepted = true; }
        else if (event.key === Qt.Key_Down) { games.incrementCurrentIndex(); event.accepted = true; }
        else if (event.key === Qt.Key_Up) { games.decrementCurrentIndex(); event.accepted = true; }
        else if (api.keys.isAccept(event)) { play(); event.accepted = true; }
    }
    Rectangle { anchors.fill: parent; color: "#10151d" }
    Image {
        anchors.fill: parent
        source: root.knownSystem ? "art/background/" + root.systemKey + ".jpg" : ""
        fillMode: Image.PreserveAspectCrop
        opacity: 0.44
        asynchronous: true
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#d9091019" }
            GradientStop { position: 0.65; color: "#30101922" }
            GradientStop { position: 1; color: "#ef090e17" }
        }
    }
    Rectangle {
        x: 32 * root.unit; y: 24 * root.unit
        width: parent.width - 64 * root.unit; height: 86 * root.unit
        radius: 8 * root.unit; border.color: "#63717e"
        gradient: Gradient {
            GradientStop { position: 0; color: "#3f4a57" }
            GradientStop { position: 0.48; color: "#222c38" }
            GradientStop { position: 1; color: "#121b26" }
        }
        Image { x: 24 * root.unit; anchors.verticalCenter: parent.verticalCenter; width: 285 * root.unit; height: 64 * root.unit; source: "art/tecnotics-logo.png"; fillMode: Image.PreserveAspectFit }
        Text { anchors { right: parent.right; rightMargin: 24 * root.unit; verticalCenter: parent.verticalCenter }; text: "TU MUNDO · TUS JUEGOS"; color: "#d8e4ed"; font.pixelSize: 15 * root.unit; font.letterSpacing: 2 * root.unit }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2 * root.unit; color: root.accent }
    }
    Text { x: 40 * root.unit; y: 136 * root.unit; text: "BIBLIOTECA / " + (root.collection ? root.collection.name.toUpperCase() : "BIENVENIDO"); color: root.accent; font.pixelSize: 15 * root.unit; font.letterSpacing: 2 * root.unit }
    Rectangle {
        id: listPanel
        x: 32 * root.unit; y: 176 * root.unit
        width: parent.width * 0.39; height: parent.height - y - 86 * root.unit
        color: "#df111923"; radius: 8 * root.unit; border.color: "#4b5c6b"
        Text { x: 20 * root.unit; y: 18 * root.unit; text: root.collection ? root.collection.games.count + " JUEGOS" : "SIN JUEGOS"; color: "#9dadbc"; font.pixelSize: 13 * root.unit; font.letterSpacing: 2 * root.unit }
        ListView {
            id: games
            anchors { fill: parent; topMargin: 54 * root.unit; bottomMargin: 12 * root.unit; leftMargin: 10 * root.unit; rightMargin: 10 * root.unit }
            model: root.collection ? root.collection.games : null
            clip: true; spacing: 5 * root.unit; keyNavigationWraps: true
            highlightMoveDuration: 130
            delegate: Rectangle {
                width: games.width; height: 49 * root.unit; radius: 4 * root.unit
                color: ListView.isCurrentItem ? "#174c61" : "transparent"
                border.color: ListView.isCurrentItem ? root.accent : "transparent"
                Text { anchors { fill: parent; leftMargin: 16 * root.unit; rightMargin: 12 * root.unit }; verticalAlignment: Text.AlignVCenter; text: modelData.title; elide: Text.ElideRight; color: "#edf5fa"; font.pixelSize: 19 * root.unit; font.bold: parent.ListView.isCurrentItem }
                MouseArea { anchors.fill: parent; onClicked: { games.currentIndex = index; root.forceActiveFocus(); }; onDoubleClicked: root.play() }
            }
        }
        Text { anchors { fill: parent; margins: 24 * root.unit }; visible: !root.collection; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap; text: "Tu arcade está listo para recibir juegos.\n\nAgrega tus juegos y sus metadatos para verlos aquí."; color: "#c4d3de"; font.pixelSize: 20 * root.unit }
    }
    Item {
        x: listPanel.x + listPanel.width + 32 * root.unit; y: listPanel.y
        width: root.width - x - 40 * root.unit; height: listPanel.height
        Image {
            id: cover
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: parent.height * 0.61
            source: root.game ? (root.game.assets.boxFront || root.game.assets.screenshot || "") : ""
            fillMode: Image.PreserveAspectFit; asynchronous: true
        }
        Image { anchors.fill: cover; visible: cover.status !== Image.Ready; source: root.knownSystem ? "art/consoles/" + root.systemKey + ".png" : "art/tecnotics-logo.png"; fillMode: Image.PreserveAspectFit }
        Text { id: title; y: parent.height * 0.65; width: parent.width; text: root.game ? root.game.title : "TECNOTICS ARCADE"; color: "white"; font.pixelSize: 28 * root.unit; font.bold: true; elide: Text.ElideRight }
        Text { anchors { top: title.bottom; topMargin: 12 * root.unit; left: parent.left; right: parent.right; bottom: parent.bottom }; text: root.game ? (root.game.description || "Selecciona JUGAR para comenzar.") : "Todos tus sistemas en un solo lugar."; color: "#c0ceda"; font.pixelSize: 17 * root.unit; wrapMode: Text.WordWrap; elide: Text.ElideRight; clip: true }
    }
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }; height: 60 * root.unit; color: "#ee101720"
        Rectangle { width: parent.width; height: root.unit; color: "#52616e" }
        Text { x: 40 * root.unit; anchors.verticalCenter: parent.verticalCenter; text: "◀  ▶  SISTEMA     ↑  ↓  ELEGIR     A / ENTER  JUGAR"; color: "#d1e1eb"; font.pixelSize: 14 * root.unit }
        Row {
            anchors { right: parent.right; rightMargin: 32 * root.unit; verticalCenter: parent.verticalCenter }; spacing: 12 * root.unit
            Repeater {
                model: ["◀", "▶", "JUGAR"]
                delegate: Rectangle {
                    width: (index === 2 ? 100 : 44) * root.unit; height: 34 * root.unit; radius: 4 * root.unit; color: "#23394a"; border.color: root.accent
                    Text { anchors.centerIn: parent; text: modelData; color: "white"; font.pixelSize: 14 * root.unit }
                    MouseArea { anchors.fill: parent; onClicked: { if (index === 2) root.play(); else root.changeSystem(index === 0 ? -1 : 1); root.forceActiveFocus(); } }
                }
            }
        }
    }
}


