$(function () {
    return fetch("/api/auth/me").then(function (response) {
        return response.json();
    }).then(function (data) {
        if (data.user_data) {
            $("#cur-user-name").text(data.user_data.username + "#" + data.user_data.discriminator);
            $("#cur-user-label").show();
            $("#login-btn").hide();
            $("#logout-btn").show();
        } else {
            $("#cur-user-name").text("");
            $("#cur-user-label").hide();
            $("#login-btn").show();
            $("#logout-btn").hide();
        }
    })
});
