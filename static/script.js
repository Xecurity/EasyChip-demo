/*
 * Copyright 2012 Bo Zhu <zhu@xecurity.ca>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


var easychip = {};


$('#buy-form').submit(function() {
    return false;  // prevent default action
});


function on_socket_open() {
    var post_data = {
        'payer_email': easychip.email_addr,
        'channel_id': easychip.channel_id
    };

    $.post('/buy', JSON.stringify(post_data), function(resp) {
        console.log(resp);
        if (resp === 'OK') {
            display_message('<div class="alert alert-info"><a class="close" data-dismiss="alert">×</a>Payment request is sent to you EasyChip app. Please check your smart phone!</div>');
        } else {
            display_message('<div class="alert alert-error"><a class="close" data-dismiss="alert">×</a>Something is wrong: ' + resp +'</div>');
            $('#buy-now').button('reset');
        }
    }, 'text').error(function(xhr) {
        console.log(xhr.responseText);
        display_message('<div class="alert alert-error"><a class="close" data-dismiss="alert">×</a>' + xhr.responseText +'</div>');
        $('#buy-now').button('reset');
    });
}


function on_socket_message(obj) {
    var message = obj.data;
    if (message === 'paid') {
        display_message('<div class="alert alert-success"><a class="close" data-dismiss="alert">×</a>Payment is successfully received! You can check the transaction history for details.</div>');
        $('#buy-now').button('reset');
    }
}


function on_socket_error(obj) {
    $('#buy-now').button('reset');
    // display_message('<div class="alert alert-error"><a class="close" data-dismiss="alert">×</a>Conn Error: ' + obj.description + '</div>');
}


$('#buy-now').click(function() {
    $('#buy-now').button('loading');

    easychip.email_addr = $('#email').val();

    if (easychip.channel_id) {
        on_socket_open();
    } else {
        $.getJSON('/channel', function(resp) {
            easychip.channel_id = resp.channel_id;

            var token = resp.token;
            var channel = new goog.appengine.Channel(token);
            var handler = {
                'onopen': on_socket_open,
            'onmessage': on_socket_message,
            'onerror': on_socket_error,
            'onclose': function() {}
            };
            channel.open(handler);
        });
    }
});


function display_message(msg) {
    $('#message').html(msg);
}


$('#history').on('show', function () {
    $.getJSON('/history', function(data) {
        var s = '';

        for (var i = 0; i < data.length; i++) {
            s += '<tr>';
            s += '<td>' + data[i].payer + '</td>';
            s += '<td>' + data[i].amount + '</td>';
            s += '<td>' + data[i].time + '</td>';
            s += '</tr>';
        }

        $('#history-list').html(s);
    });
});


var _gaq = _gaq || [];
_gaq.push(['_setAccount', 'UA-33819775-1']);
_gaq.push(['_trackPageview']);

(function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
})();
