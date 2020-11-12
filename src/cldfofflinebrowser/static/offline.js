OFFLINE = {};

OFFLINE.AudioPlayer = (function () {
    var paused = true,
        playlist_index = -1,
        playlist,
        control;

    var _play = function () {
        var layer, audio;

        if (paused) return;
        if (playlist_index >= 0 && playlist_index < playlist.length) {
            playlist[playlist_index].closePopup();
        }
        playlist_index++;
        if (playlist_index === playlist.length) {
            playlist_index = 0;
        }
        layer = playlist[playlist_index];
        layer.openPopup();
        audio = $('#' + layer.audio_id);
        if (audio.length) {
            audio[0].addEventListener('ended', _play);
            audio[0].play();
        } else {
            _play();
        }
    }

    var _control_button = function (type, container, title, linktext, callable, ctx) {
        var button = L.DomUtil.create('a', 'leaflet-control-audioplayer-' + type, container);
        button.href = '#';
        button.title = title;
        button.style.cssText = 'font-size: 22px;';
        button.innerText = linktext;
        L.DomEvent.on(
            button,
            'click',
            function (e) {
                L.DomEvent.stopPropagation(e);
                L.DomEvent.preventDefault(e);
                callable();
            },
            ctx);
        return button;
    }

    return {
        init: function (layers) {
            playlist = layers;
            playlist.sort(function (e1, e2) {
                // sort by latitude, North to South:
                return e2._latlng.lat - e1._latlng.lat
            });
        },
        play: function () {
            if (paused) {
                paused = false;
                $('.leaflet-control-audioplayer-play')[0].innerText = '⏸';
            } else {
                paused = true;
                $('.leaflet-control-audioplayer-play')[0].innerText = '▶';
            }
            _play();
        },
        stop: function () {
            var player = $('.leaflet-control-audioplayer-play');
            if (player.length) {
                player[0].innerText = '▶';
            }
            paused = true;
            playlist_index = -1;
        },
        addToMap: function (themap) {
            map = themap;
            L.Control.AudioPlayer = L.Control.extend({
                options: {position: 'topleft'},
                onAdd: function (map) {
                    var container = L.DomUtil.create('div', 'leaflet-control-audioplayer leaflet-bar leaflet-control');
                    this.link = _control_button('play', container, 'Play audio', '▶', OFFLINE.AudioPlayer.play, this);
                    this.stop = _control_button('stop', container, 'Stop audio', '⏹', OFFLINE.AudioPlayer.stop, this);
                    return container;
                }
            });
            L.control.audioplayer = function (opts) {
                return new L.Control.AudioPlayer(opts);
            }
            control = L.control.audioplayer();
            control.addTo(themap);
        }
    }
})();

OFFLINE.Map = (function () {
    var map, markers = [];

    var redDot = L.icon({
        iconUrl: 'data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogICAgICB4bWxuczp4bGluaz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94bGluayIgaGVpZ2h0PSI0MCIgd2lkdGg9IjQwIj4KICA8Y2lyY2xlIGN4PSIyMCIgY3k9IjIwIiByPSIxNCIgc3R5bGU9ImZpbGw6I0ZGMDAwMDtzdHJva2U6YmxhY2s7c3Ryb2tlLXdpZHRoOjFweDtzdHJva2UtbGluZWNhcDpyb3VuZDtzdHJva2UtbGluZWpvaW46cm91bmQ7Ii8+Cjwvc3ZnPg==',
        iconSize: [20, 20], // size of the icon
        iconAnchor: [10, 10], // point of the icon which will correspond to marker's location
        popupAnchor: [0, 0] // point from which the popup should open relative to the iconAnchor
    });

    var audio_element = function(spec) {
        var html = "<audio class='popup-audio' controls='controls'>";
        html += "<source src='" + spec.name + "' type='" + spec.mimetype + "'>";
        html += "Your browser does not support the audio element.";
        html += "</audio>";
        return html
    }

    return {
        init: function () {
            var has_audio = false,
                popup_content;
            map = L.map('map', {fullscreenControl: true});
            L.tileLayer(
                '../tiles/{z}/{x}/{y}.png',
                {
                    minZoom: options['minZoom'],
                    maxZoom: options['maxZoom'],
                    attribution:
                        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }).addTo(map);

            // bind popup with language name and transcription and audio element
            for (var l in data['languages']) {
                lang = data['languages'][l];
                popup_content = "<b>" + lang['Name'] + ":</b> " + data['forms'][l]['form'];
                marker = L.marker([lang['latitude'], lang['longitude']], {icon: redDot}).addTo(map);
                if (data['forms'][l]['audio']) {
                    marker.audio_id = 'audio-' + l;
                    has_audio = true;
                    popup_content += "<br>" + audio_element(data['forms'][l]['audio']);
                }
                marker.bindPopup(popup_content);
                marker.bindTooltip(data['forms'][l]['form'], {permanent: true, opacity: 0.5});
                markers.push(marker);
            }

            var group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds());

            if (has_audio) {
                OFFLINE.AudioPlayer.addToMap(map);
                OFFLINE.AudioPlayer.init(markers);
            } else {
                map.eachLayer(function (layer) {layer.openTooltip()})
            }
        }
    }
})();


$(document).ready(function () {
    OFFLINE.Map.init();
});
