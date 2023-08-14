// 为话题创建一个聊天按钮
function createChatButton(topic) {
    let chatButton = document.createElement("button");
    chatButton.innerText = topic.theme;
    chatButton.classList.add("chat-button");
    chatButton.onclick = function () {
        handleChatButtonClick(topic.id);
    };
    return chatButton;
}

// 处理聊天按钮的点击事件
function handleChatButtonClick(topic_id) {
    axios.post('/change_theme/', {
        topic_id: topic_id
    }, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(function (response) {
            displayChatHistory(response.data.records);
            setActiveButton(topic_id);
        })
        .catch(function (error) {
            console.error('An error occurred:', error);
        });
}

// 显示聊天历史
function displayChatHistory(records) {
    let chatDisplay = document.getElementById("chat-display");
    chatDisplay.innerHTML = '';  // 清空显示

    records.forEach(function (record) {
        let userMessage = document.createElement("p");
        userMessage.innerText = record.user + ": " + record.text;
        chatDisplay.appendChild(userMessage);

        let botMessage = document.createElement("p");
        botMessage.innerText = "Bot: " + record.bot_reply;
        chatDisplay.appendChild(botMessage);
    });
}

// 将点击的按钮设置为活跃状态
function setActiveButton(topic_id) {
    let buttons = document.querySelectorAll('.chat-button');
    buttons.forEach(function (btn) {
        btn.classList.remove('active');
        if (btn.dataset.topicId === topic_id) {
            btn.classList.add('active');
        }
    });
}

// 从服务器获取并展示聊天历史数据
function populateChatHistory() {
    axios.get('/chat/homepage/', {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(function (response) {
            let chatHistoryContainer = document.getElementById("chat-history");
            response.data.topics.forEach(function (topic) {
                let chatButton = createChatButton(topic);
                chatButton.dataset.topicId = topic.id;  // 为每个按钮添加一个数据属性，存储其话题ID
                chatHistoryContainer.appendChild(chatButton);
            });
        })
        .catch(function (error) {
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
            if (response.data.topic && response.data.topic.theme) {
                let themeList = document.getElementById('chat-history');
                let newThemeButton = createChatButton(response.data.topic);
                themeList.insertBefore(newThemeButton, themeList.firstChild);
            }
        })
        .catch(function (error) {
            console.error("Error creating new theme:", error);
        });
}

// 处理文本输入
var textInput = document.getElementById("text-input");
textInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        axios.post('/chat/receive_text/', {
            text: textInput.value
        }, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(function (response) {
                let userText = response.data.conversation.prompt;

                if (response.data.type === 'existing_topic') {
                    let chatDisplay = document.getElementById("chat-display");

                    let userMessage = document.createElement("p");
                    userMessage.innerText = "You: " + userText;
                    chatDisplay.appendChild(userMessage);
                } else if (response.data.type === 'new_topic') {
                    let themeList = document.getElementById('chat-history');
                    let newThemeButton = createChatButton(response.data.topic);
                    themeList.insertBefore(newThemeButton, themeList.firstChild);

                    let chatDisplay = document.getElementById("chat-display");
                    chatDisplay.innerHTML = '';  // 清空显示

                    let userMessage = document.createElement("p");
                    userMessage.innerText = "You: " + userText;
                    chatDisplay.appendChild(userMessage);
                }
                textInput.value = ""; // 清空输入框
            })
            .catch(function (error) {
                console.error('Failed to send text:', error);
            });
    }
});

let mediaRecorder;
let recordedChunks = [];
let recordingTimeout;

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(function(stream) {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = function(event) {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };
            mediaRecorder.onstop = sendAudioData;
            mediaRecorder.start();
            document.getElementById("voice-button").innerText = "停止录音";
            document.getElementById("voice-button").classList.add('recording'); // 添加录音时的样式

            // 设置 25 秒的定时器
            recordingTimeout = setTimeout(() => {
                if (mediaRecorder && mediaRecorder.state === "recording") {
                    stopRecording();
                }
            }, 25000);  // 25 秒
        })
        .catch(function(err) {
            console.error('Failed to start recording:', err);
        });
}

function stopRecording() {
    if (mediaRecorder) {
        mediaRecorder.stop();
    }
    document.getElementById("voice-button").innerText = "开始录音";
    document.getElementById("voice-button").classList.remove('recording'); // 移除录音时的样式

    // 清除定时器，确保不会多次触发
    if (recordingTimeout) {
        clearTimeout(recordingTimeout);
        recordingTimeout = null;
    }
}

function sendAudioData() {
    let audioBlob = new Blob(recordedChunks, {type: 'audio/wav'});
    let formData = new FormData();
    formData.append('audio', audioBlob);

    axios.post('/chat/receive_audio/', formData, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'multipart/form-data'
        }
    })
        .then(function (response) {
            // 根据您的具体后端逻辑进行处理，例如显示机器人的回复
        })
        .catch(function (error) {
            console.error('Failed to send audio data:', error);
        });

    recordedChunks = [];
}

document.getElementById("voice-button").onclick = function () {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        stopRecording();
    } else {
        startRecording();
    }
};

// 处理“新聊天”按钮
document.getElementById("new-chat-button").onclick = function () {
    createNewChat();
};

populateChatHistory();
