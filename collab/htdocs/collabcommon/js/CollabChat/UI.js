define([
    "collabcommon/js/common/EventSource",
    "collabcommon/js/common/dom",
], function(
    EventSource,
    dom
) {
    "use strict";
    
    var pad = function(number, length) {
        number = "" + number;
        while (number.length < length) {
            number = "0" + number;
        }
        return number;
    };

    var formatTime = function(timestamp) {
        var dateObj = new Date(timestamp);
        return {
            time: (pad(dateObj.getHours(), 2) + ":" +
                   pad(dateObj.getMinutes(), 2)),
            date: (pad(dateObj.getFullYear(), 4) + "-" +
                   pad(dateObj.getMonth() + 1, 2) + "-" +
                   pad(dateObj.getDate(), 2))
        };
    };

    var linkRex = /https?:\/\/\S+/g;
    var linkify = function(text, linkAttributes) {
        var result = [];

        linkRex.lastIndex = 0;
        while (true) {
            var start = linkRex.lastIndex;
            var match = linkRex.exec(text);

            var end = match ? match.index : text.length;
            if (start < end) {
                var bite = text.slice(start, end);
                result.push(document.createTextNode(bite));
            }

            if (!match) {
                break;
            }

            var a = document.createElement("a");
            a.href = match[0];
            a.rel = "noreferrer";
            a.target = "blank";
            a.appendChild(document.createTextNode(match[0]));
            result.push(a);
        }

        return result;
    };

    var lineRex = /\r\n|\r|\n/;
    var lineify = function(string) {
        var bites = string.split(lineRex);

        var result = [];
        result.push.apply(result, linkify(bites[0]));

        for (var i = 1, len = bites.length; i < len; i++) {
            result.push(document.createElement("br"));
            result.push.apply(result, linkify(bites[i]));
        }

        return result;
    };

    var hash = function(string) {
        // Return a value between 0.0 and 1.0 based on the input
        // string. This is an ad-hoc algorithm, implementing some
        // proper hash algorithm recommended.

        var result = 0x1337;

        for (var i = 0, len = string.length; i < len; i++) {
            var code = string.charCodeAt(i);
            result = (result ^ (code * code * 11 * 19)) & 0xffff;
        }

        return result / 0xffff;
    };

    var hsvFill = ["000000", "00000", "0000", "000", "00", "0", ""];
    var hsv = function(h, s, v) {
        // Hue (h), saturation (s) and value (v) should be values
        // between 0.0 and 1.0 (inclusive). Returns color in
        // format #RRGGBB.

        h = (h * 6) % 6;
        s = Math.max(Math.min(s, 1.0), 0.0);
        v = Math.max(Math.min(v, 1.0), 0.0);

        var max = v;
        var min = v * (1 - s);
        var mid = min + (max - min) * (1 - Math.abs(1 - h % 2));
        var maxMidMin = [max, mid, min, min, mid, max];

        var r = (255 * maxMidMin[((h + 0) % 6) | 0]) | 0;
        var g =  (255 * maxMidMin[((h + 4) % 6) | 0]) | 0;
        var b = (255 * maxMidMin[((h + 2) % 6) | 0]) | 0;

        var total = ((r << 16) + (g << 8) + b).toString(16);
        return "#" + hsvFill[total.length] + total;
    };

    var trim = function(string) {
        return string.match(/^\s*(.*?)\s*$/)[1];
    };

    var createElement = function(tag, className) {
        var element = document.createElement(tag);
        element.className = className;
        return element;
    };

    var appendText = function(element, text) {
        element.appendChild(document.createTextNode(text));
    };

    var UI = function(container) {

        this.container = container;

        this.tools = createElement("div", "toolbar");
        this.toolset = createElement("div", "toolset");
        this.channelLabel = createElement("span", "channel-label");
        this.connectionStatus = createElement("span", "connection-status");
        this.tools.appendChild(this.channelLabel);
        this.toolset.appendChild(this.connectionStatus);
        this.tools.appendChild(this.toolset);
        this.container.appendChild(this.tools);

        this.chatWrapper = createElement("div", "chat-wrapper");

        this.chat = createElement("div", "chat");
        this.chatWrapper.appendChild(this.chat);

        this.userlistContainer = createElement("div", "userlist");
        this.userlist = createElement("ul", "users");
        this.userlistContainer.appendChild(this.userlist);

        this.chatWrapper.appendChild(this.userlistContainer);
        this.container.appendChild(this.chatWrapper);

        this.area = createElement("div", "output");
        this.areaContainer = createElement("div", "output-container");
        this.areaContainer.appendChild(this.area);
        this.chat.appendChild(this.areaContainer);

        this.input = createElement("input", "input");
        this.input.placeholder = "<write your message here>";
        this.inputContainer = createElement("div", "input-container");
        this.inputContainer.appendChild(this.input);
        this.chat.appendChild(this.inputContainer);

        this.isAtBottom = true;
        this.previous = {};

        var _this = this;
        dom.listen(this.areaContainer, "scroll", function(event) {
            _this.isAtBottom = (this.scrollTop + this.clientHeight) === this.scrollHeight;
        });

        dom.listen(this.areaContainer, "mousewheel", this.preventWheelGestures.bind(this));
        dom.listen(this.areaContainer, "wheel", this.preventWheelGestures.bind(this));
        dom.listen(this.userlistContainer, "mousewheel", this.preventWheelGestures.bind(this));
        dom.listen(this.userlistContainer, "wheel", this.preventWheelGestures.bind(this));

        dom.listen(window, "resize", function() {
            if (_this.isAtBottom) {
                _this._scrollToBottom();
            }
        });
        dom.listen(this.input, "keypress", function(event) {
            if (event.keyCode !== 13) {
                return true;
            }

            var text = trim(this.value);
            this.value = "";
            if (text) {
                _this.trigger("output", text);
            }
            _this._scrollToBottom();
            return false;
        });
    };

    UI.prototype = new EventSource(this);

    UI.prototype.addMessage = function(timestamp, sender, body) {
        var formatted = formatTime(timestamp);
        var previous = this.previous;
        this.previous = formatted;

        var dateDiv = null;
        if (formatted.date !== previous.date) {
            dateDiv = createElement("div", "message");
            var bodyDiv = createElement("div", "room-message");
            appendText(bodyDiv, "day changed to " + formatted.date);
            dateDiv.appendChild(bodyDiv);
        }

        var msgDiv = createElement("div", "message");

        if (sender !== null) {
            var hashed = hash(sender);
            var hue = hashed;
            var value = 0.97 + 0.03 * ((hashed * 1000) % 1.0);

            msgDiv.style.background = hsv(hue, 0.02, 0.98);

            var timeDiv = createElement("div", "time");
            appendText(timeDiv, formatted.time);
            msgDiv.appendChild(timeDiv);

            var senderDiv = createElement("div", "sender");
            senderDiv.style.color = hsv(hue, 0.35, 0.575);
            // Whitespaces around the sender make copy-pastes clearer.
            appendText(senderDiv, sender);
            msgDiv.appendChild(senderDiv);

            var bodyDiv = createElement("div", "body");
            bodyDiv.style.color = hsv(hue, 0.1, 0.3);

            var bites = lineify(body);
            for (var i = 0, len = bites.length; i < len; i++) {
                bodyDiv.appendChild(bites[i]);
            }
            msgDiv.appendChild(bodyDiv);
        } else {
            var bodyDiv = createElement("div", "room-message");
            appendText(bodyDiv, body);
            msgDiv.appendChild(bodyDiv);
        }

        var wasAtBottom = this.isAtBottom;

        if (dateDiv) {
            this.area.appendChild(dateDiv);
        }
        this.area.appendChild(msgDiv);

        if (wasAtBottom) {
            this._scrollToBottom();
        }
    };

    UI.prototype._scrollToBottom = function() {
        this.areaContainer.scrollTop = this.areaContainer.scrollHeight;
    };

    UI.prototype.connectionStatusChanged = function(status) {
        this.connectionStatus.textContent = status.toLowerCase();
    };

    UI.prototype.userJoin = function(key, value) {
        var user = createElement("li", "user");
        user.id = key;
        user.textContent = key;
        this.userlist.appendChild(user);
    };

    UI.prototype.userLeave = function(key) {
        var user = document.getElementById(key);
        this.userlist.removeChild(user);
    };

    UI.prototype.onDisconnect = function() {
        var users = this.userlist;
        while (users.firstChild) {
            this.userlist.removeChild(users.firstChild);
        }
    };

    UI.prototype.setChannelLabel = function(label) {
        this.channelLabel.textContent = label;
    };

    UI.prototype.preventWheelGestures = function(event, _element) {
        var element = _element || event.currentTarget;

        var deltaX = 0;
        var deltaY = 0;
        if (event.type === "mousewheel") {
            deltaX = -(event.wheelDeltaX || 0);
            deltaY = -(event.wheelDeltaY || (deltaX === 0 ? event.wheelDelta : 0)) || 0;
        } else if (event.type === "wheel") {
            deltaX = event.deltaX;
            deltaY = event.deltaY;
        }

        var left = element.scrollLeft;
        var ignoreX =
            (deltaX === 0) ||
            (deltaX > 0 && left >= element.scrollWidth - element.clientWidth) ||
            (deltaX < 0 && left <= 0);

        var top = element.scrollTop;
        var ignoreY =
            (deltaY === 0) ||
            (deltaY > 0 && top >= element.scrollHeight - element.clientHeight) ||
            (deltaY < 0 && top <= 0);

        if (!ignoreX && deltaX > 0 && left === element.scrollWidth - element.clientWidth - 1) {
            element.scrollLeft += 1;
            ignoreX = true;
        }
        if (!ignoreY && deltaY > 0 && top === element.scrollHeight - element.clientHeight - 1) {
            element.scrollTop += 1;
            ignoreY = true;
        }

        if (ignoreX && ignoreY) {
            event.stopPropagation();
            event.preventDefault();
            return false;
        }
        return true;
    };

    return UI;
});