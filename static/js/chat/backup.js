function populateChatHistory() {
    axios.get('/chat/homepage/', {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(function(response) {
        var chatHistoryContainer = document.getElementById("chat-history");
        response.data.topics.forEach(function(topic) {
            var chatButton = document.createElement("button");
            chatButton.innerText = topic.theme;  // 注意这里使用了topic.theme
            chatButton.classList.add("chat-button");
            chatButton.onclick = function() {
                axios.post('/change_theme/', {
                    theme: topic.theme  // 注意这里使用了topic.theme
                }, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(function(response) {
                    var chatDisplay = document.getElementById("chat-display");
                    chatDisplay.innerHTML = '';  // 清空显示

                    response.data.records.forEach(function(record) {
                        var userMessage = document.createElement("p");
                        userMessage.innerText = record.user + ": " + record.text;
                        chatDisplay.appendChild(userMessage);

                        var botMessage = document.createElement("p");
                        botMessage.innerText = "Bot: " + record.bot_reply;
                        chatDisplay.appendChild(botMessage);
                    });

                })
                .catch(function(error) {
                    console.error('An error occurred:', error);
                });

                // 将点击的按钮设置为活跃状态
                let buttons = document.querySelectorAll('.chat-button');
                buttons.forEach(function(btn) {
                    btn.classList.remove('active');
                });
                chatButton.classList.add('active');
            };
            chatHistoryContainer.appendChild(chatButton);
        });
    })
    .catch(function(error) {
        console.error('An error occurred:', error);
    });
}


function createNewChat() {
    axios.post('/chat/create_chat/', {}, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(function (response) {
        if (response.data.topic && response.data.topic.theme) {  // 注意这里我们获取topic对象然后取其theme属性
            let themeList = document.getElementById('chat-history');
            let newThemeButton = document.createElement('button');
            newThemeButton.innerText = response.data.topic.theme;  // 注意这里使用了response.data.topic.theme
            newThemeButton.classList.add("chat-button");
            themeList.insertBefore(newThemeButton, themeList.firstChild);
        }
    })
    .catch(function (error) {
        console.error("Error creating new theme:", error);
    });
}


// 处理文本输入
var textInput = document.getElementById("text-input");
textInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        axios.post('/chat/receive_text/', {
            text: textInput.value
        }, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(function(response) {
            // TODO: 根据服务器响应更新前端显示
            textInput.value = ""; // 清空输入框
        })
        .catch(function(error) {
            console.error('Failed to send text:', error);
        });
    }
});

// 处理“新聊天”按钮
document.getElementById("new-chat-button").onclick = function() {
    createNewChat();
};

populateChatHistory();
