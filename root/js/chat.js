// Append a new message
function addMessage(time, author, content, type, filename = "unnamed") {
  // Get the conversation container element
  var container = document.getElementById("chat-container");

  // Create a new message element
  var messageElement = document.createElement("div");
  messageElement.className = "message";

  // Create a new author element
  var authorElement = document.createElement("div");
  authorElement.className = "author";
  authorElement.innerText = author;

  // Create a new time element
  var timeElement = document.createElement("div");
  timeElement.className = "time";
  timeElement.innerText = time;

  // Create a new content element
  var contentElement;
  switch (type) {
    case "text":
      // Text
      contentElement = document.createElement("div");
      contentElement.className = "text";
      contentElement.innerText = content;
      break;
    case "image":
      contentElement = document.createElement("img");
      contentElement.src = "/get_message_content/" + content;
      break;
    case "file":
      contentElement = document.createElement("a");
      contentElement.className = "text";
      contentElement.innerText = filename + "\n---Click to download---";
      contentElement.href = "/get_message_content/" + content;
      break;
  }

  // Add the author, time, and text elements to the message element
  messageElement.appendChild(authorElement);
  messageElement.appendChild(timeElement);
  messageElement.appendChild(contentElement);

  // Add the message element to the conversation container
  container.appendChild(messageElement);

  return messageElement;
}

// Send message
export async function sendMessage() {
  // Initialize message object
  const message = {};

  // Get user input
  const userInputElement = document.getElementById("user-input");
  if (userInputElement.value === "") {
    return;
  }

  // Get content type
  message.type = document.querySelector("#input-type").value;

  // Get username
  message.author = document.getElementById("username").value;
  if (message.author === "") {
    alert("Please enter your username.");
    return;
  }

  // Get content
  if (message.type === "text") {
    message.filename = "text.txt";

    const text = userInputElement.value;

    const encoder = new TextEncoder();
    const utf8Array = encoder.encode(text);

    message.content = btoa(String.fromCharCode(...utf8Array));
  } else {
    message.filename = userInputElement.files[0].name;

    const reader = new FileReader();
    reader.readAsDataURL(userInputElement.files[0]);

    message.content = await new Promise((resolve, reject) => {
      reader.onload = () => {
        resolve(reader.result.split(",")[1]);
      };
    });
  }

  // Send message to server
  const response = await fetch("/send_message", {
    method: "POST",
    body: JSON.stringify(message)
  }).then((res) => res.json());

  if (response.err !== undefined) {
    alert("Error: " + response.err);
    return;
  }

  // Clean input field and refresh chat
  userInputElement.value = "";
  refreshChat();
}


// Refresh chat messages
export async function refreshChat(messagesCount = 15) {
  const chatContainer = document.getElementById("chat-container");

  // Clear existing messages
  while (chatContainer.children.length) {
    chatContainer.removeChild(chatContainer.children[0]);
  }

  // Fetch latest messages
  try {
    const response = await fetch("/get_messages", {
      method: "POST",
      body: JSON.stringify({
        count: messagesCount,
      }),
    });

    const messages = await response.json();

    if (messages.err !== undefined) {
      alert("Error: " + messages.err);
      return;
    }

    for (const msg of messages) {
      if (msg.type === "text") {
        const content = await fetch("/get_message_content/" + msg.hash).then((res) => res.text());
        addMessage(msg.time, msg.author, content, "text");
      } else {
        addMessage(msg.time, msg.author, msg.hash, msg.type, msg.filename);
      }
    }
  } catch (error) {
    console.error("Error fetching messages:", error);
  }
}