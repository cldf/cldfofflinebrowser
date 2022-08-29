OFFLINE = {};

OFFLINE.AudioPlayer = (function () {
    var paused = true,
        playlist_index = -1,
        playlist,
        control,
        play_initial_bounds;

    var play_btn_img = '<img class="btn-ctrl-img" title="Play all audio within the current map section from north to south" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxOCIgaGVpZ2h0PSIxOCIgdmlld0JveD0iMCAwIDggOCI+PHBhdGggZD0iTTAgMHY2bDYtMy02LTN6IiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxIDEpIi8+PC9zdmc+" />';
    var stop_btn_img = '<img class="btn-ctrl-img" title="Stop audio" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxOCIgaGVpZ2h0PSIxOCIgdmlld0JveD0iMCAwIDggOCI+PHBhdGggZD0iTTAgMHY2aDZ2LTZoLTZ6IiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxIDEpIi8+PC9zdmc+" />';
    var pause_btn_img = '<img class="btn-ctrl-img" title="Pause audio" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxOCIgaGVpZ2h0PSIxOCIgdmlld0JveD0iMCAwIDggOCI+PHBhdGggZD0iTTAgMHY2aDJ2LTZoLTJ6bTQgMHY2aDJ2LTZoLTJ6IiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxIDEpIi8+PC9zdmc+" />';

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
        // play only those audio which is currently shown at map bounds
        if (play_initial_bounds.contains(layer.getLatLng())) {
            layer.openPopup();
            audio = $('#' + layer.audio_id);
            if (audio.length) {
                audio[0].addEventListener('ended', _play);
                audio[0].play();
            } else {
                _play();
            }
        } else {
            _play();
        }
    }

    var _control_button = function (type, container, linktext, callable, ctx) {
        var button = L.DomUtil.create('a', 'leaflet-control-audioplayer-' + type, container);
        button.href = '#';
        button.innerHTML = linktext;
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
                $('.leaflet-control-audioplayer-play')[0].innerHTML = pause_btn_img;
            } else {
                paused = true;
                $('.leaflet-control-audioplayer-play')[0].innerHTML = play_btn_img;
            }
            // remember globally the inital bounds
            // due to possible shifting the map while open a popup
            play_initial_bounds = map.getBounds();
            _play();
        },
        stop: function () {
            var player = $('.leaflet-control-audioplayer-play');
            if (player.length) {
                player[0].innerHTML = play_btn_img;
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
                    this.link = _control_button('play', container, play_btn_img, OFFLINE.AudioPlayer.play, this);
                    this.stop = _control_button('stop', container, stop_btn_img, OFFLINE.AudioPlayer.stop, this);
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
        html += "<source src='" + spec.name + "' type='" + spec.mediaType + "'>";
        html += "Your browser does not support the audio element.";
        html += "</audio>";
        return html
    }

    return {
        init: function () {
            var has_audio = false,
                popup_content;
            map = L.map('map', {fullscreenControl: true});
            var tilesURL = 'tiles/{z}/{x}/{y}.png';
            if (!data['index']) {
              tilesURL = '../' + tilesURL;
            }
            L.tileLayer(
                tilesURL,
                {
                    minZoom: options['minZoom'],
                    maxZoom: options['maxZoom'],
                    attribution:
                        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }).addTo(map);

            // bind popup with language name and transcription and audio element
            var tooltip_opts = {permanent: true, opacity: 0.75, interactive: true};
            for (var l in data['languages']) {
                lang = data['languages'][l];
                if (data['index']) {
                    popup_content = "<b>" + lang['Name'] + "</b>";
                    marker = L.marker([lang['latitude'], lang['longitude']], {icon: redDot}).addTo(map);
                    marker.bindPopup(popup_content);
                    marker.bindTooltip(lang['Name'], tooltip_opts);
                } else {
                    popup_content = "<b>" + lang['Name'] + ":</b> " + data['forms'][l]['form'];
                    marker = L.marker([lang['latitude'], lang['longitude']], {icon: redDot}).addTo(map);
                    if (data['forms'][l]['audio']) {
                        marker.audio_id = 'audio-' + l;
                        has_audio = true;
                        popup_content += "<br>" + audio_element(data['forms'][l]['audio']);
                    }
                    marker.bindPopup(popup_content);
                    marker.bindTooltip(data['forms'][l]['form'], tooltip_opts);
                }
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
