// Constants
const MAX_CONTENT_BYTES = 0x1000000;

// From https://geraintluff.github.io/sha256/
var sha256 = function sha256(ascii) {
  function rightRotate(value, amount) {
    return (value >>> amount) | (value << (32 - amount));
  };

  var mathPow = Math.pow;
  var maxWord = mathPow(2, 32);
  var lengthProperty = "length";
  var i, j; // Used as a counter across the whole file
  var result = '';

  var words = [];
  var asciiBitLength = ascii[lengthProperty] * 8;

  //* caching results is optional - remove/add slash from front of this line to toggle
  // Initial hash value: first 32 bits of the fractional parts of the square roots of the first 8 primes
  // (we actually calculate the first 64, but extra values are just ignored)
  var hash = sha256.h = sha256.h || [];
  // Round constants: first 32 bits of the fractional parts of the cube roots of the first 64 primes
  var k = sha256.k = sha256.k || [];
  var primeCounter = k[lengthProperty];
  /*/
  var hash = [], k = [];
  var primeCounter = 0;
  //*/

  var isComposite = {};
  for (var candidate = 2; primeCounter < 64; candidate++) {
    if (!isComposite[candidate]) {
      for (i = 0; i < 313; i += candidate) {
        isComposite[i] = candidate;
      }
      hash[primeCounter] = (mathPow(candidate, .5) * maxWord) | 0;
      k[primeCounter++] = (mathPow(candidate, 1 / 3) * maxWord) | 0;
    }
  }

  ascii += "\x80" // Append Ƈ' bit (plus zero padding)
  while (ascii[lengthProperty] % 64 - 56) ascii += "\x00" // More zero padding
  for (i = 0; i < ascii[lengthProperty]; i++) {
    j = ascii.charCodeAt(i);
    if (j >> 8) return; // ASCII check: only accept characters in range 0-255
    words[i >> 2] |= j << ((3 - i) % 4) * 8;
  }
  words[words[lengthProperty]] = ((asciiBitLength / maxWord) | 0);
  words[words[lengthProperty]] = (asciiBitLength)

  // process each chunk
  for (j = 0; j < words[lengthProperty];) {
    var w = words.slice(j, j += 16); // The message is expanded into 64 words as part of the iteration
    var oldHash = hash;
    // This is now the undefined working hash", often labelled as variables a...g
    // (we have to truncate as well, otherwise extra entries at the end accumulate
    hash = hash.slice(0, 8);

    for (i = 0; i < 64; i++) {
      var i2 = i + j;
      // Expand the message into 64 words
      // Used below if
      var w15 = w[i - 15],
        w2 = w[i - 2];

      // Iterate
      var a = hash[0],
        e = hash[4];
      var temp1 = hash[7] +
        (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25)) // S1
        +
        ((e & hash[5]) ^ ((~e) & hash[6])) // ch
        +
        k[i]
        // Expand the message schedule if needed
        +
        (w[i] = (i < 16) ? w[i] : (
          w[i - 16] +
          (rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3)) // s0
          +
          w[i - 7] +
          (rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10)) // s1
        ) | 0);
      // This is only used once, so *could* be moved below, but it only saves 4 bytes and makes things unreadble
      var temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)) // S0
        +
        ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2])); // maj

      hash = [(temp1 + temp2) | 0].concat(hash); // We don't bother trimming off the extra ones, they're harmless as long as we're truncating when we do the slice()
      hash[4] = (hash[4] + temp1) | 0;
    }

    for (i = 0; i < 8; i++) {
      hash[i] = (hash[i] + oldHash[i]) | 0;
    }
  }

  for (i = 0; i < 8; i++) {
    for (j = 3; j + 1; j--) {
      var b = (hash[i] >> (j * 8)) & 255;
      result += ((b < 16) ? 0 : '') + b.toString(16);
    }
  }
  return result;
};

// Append a new message
function addMessage(timestamp, author, content, type, filename) {
  // Get the conversation container element
  var container = document.getElementById("chat-container");

  // Create a new message element
  var messageElement = document.createElement("div");
  messageElement.className = "message";
  messageElement.setAttribute("timestamp", timestamp);

  // Create a new author element
  var authorElement = document.createElement("div");
  authorElement.className = "author";
  authorElement.innerText = author;

  // Create a new time element
  var timeElement = document.createElement("div");
  timeElement.className = "time";
  timeElement.innerText = new Date(timestamp).toLocaleString();

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
    case "audio":
    case "video":
      contentElement = document.createElement(type);
      contentElement.src = "/get_message_content/" + content;
      contentElement.controls = true;
      break;
    case "file":
      contentElement = document.createElement("a");
      contentElement.className = "text";
      contentElement.innerText = filename;
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
  // Get user input
  const inputElement = document.getElementById("user-input");
  if (inputElement.value === "") {
    return;
  }

  // Initialize a message object
  var message = {};

  // Get username
  message.author = document.getElementById("username").value;
  if (message.author === "") {
    alert("Please enter your username.");
    return;
  }

  // Show status
  document.getElementById("status").style.display = "";
  document.getElementById('status-text').innerText = "";
  document.getElementById('status-progress').removeAttribute("value");

  // Disable send button
  var sendButton = document.getElementById("send-button");
  sendButton.disabled = true;
  inputElement.disabled = true;

  // Get content type
  message.type = document.querySelector("#input-type").value;

  // Get content
  document.getElementById("status-text").innerText = "Status: Reading content...";

  var contentData = {};
  if (message.type === "text") {
    message.filename = "text.txt";
    let text = inputElement.value;
    let encoder = new TextEncoder();
    let utf8Array = encoder.encode(text);
    contentData.content = utf8Array;
  } else {
    message.filename = inputElement.files[0].name;
    let reader = new FileReader();
    reader.readAsArrayBuffer(inputElement.files[0]);
    contentData.content = await new Promise((resolve, reject) => {
      reader.onload = () => resolve(new Uint8Array(reader.result));
    });
  }

  // Convert Uint8Array to String
  var partCount = Math.ceil(contentData.content.length / 65536);
  var stringContent = "";

  document.getElementById("status-progress").max = partCount;
  for (let i = 0; i < partCount; i++) {
    stringContent += String.fromCharCode.apply(null, contentData.content.slice(65536 * i, 65536 * (i + 1)));

    document.getElementById("status-text").innerText = "Status: Converting Uint8Array to String... (" + i + "/" + partCount + ")";
    document.getElementById("status-progress").value = i;
  }
  document.getElementById("status-progress").removeAttribute("value");

  contentData = null;
  partCount = null;

  // Calculate hash
  document.getElementById("status-text").innerText = "Status: Calculating hash of content...";
  message.hash = sha256(stringContent);

  // Send a message index to the server
  document.getElementById("status-text").innerText = "Status: Sending index of the message to server...";

  var response = await fetch("/send_message", {
    method: "POST",
    body: JSON.stringify(message),
  }).then(res => res.json());

  // Handle error response
  if (response.err !== undefined) {
    alert("Error: " + response.err);
    return;
  }
  response = null;

  // Base64 Encode
  document.getElementById("status-text").innerText = "Status: Converting String to Base64...";

  var base64Content = btoa(stringContent);
  stringContent = null;

  // Send content of the message to the server
  document.getElementById("status-progress").max = base64Content.length;

  var hash = message.hash;
  let seek = 0;

  message = null;
  do {
    document.getElementById("status-text").innerText = "Status: Pushing content to server... (" + seek + "/" + base64Content.length + ")";
    document.getElementById('status-progress').value = seek;

    let pushBody = {
      eof: false,
      hash: hash,
      content: base64Content.slice(seek, seek + MAX_CONTENT_BYTES)
    };

    pushBody.eof = (base64Content.length - seek) <= MAX_CONTENT_BYTES;

    try {
      const response = await fetch("/push_content", {
        method: "POST",
        body: JSON.stringify(pushBody)
      });
      const responseBody = await response.json();
      if (responseBody.err !== undefined) {
        alert("Error: " + responseBody.err);
        return;
      }
    } catch (error) {
      alert("Error sending content: " + error);
      return;
    }

    seek += pushBody.content.length;
  } while (seek < base64Content.length);

  // Clean up
  inputElement.disabled = false;
  sendButton.disabled = false;
  inputElement.value = "";

  document.getElementById("status").style.display = "none";
}


// Refresh chat messages
export async function refreshChat(messagesCount = 15) {
  const chatContainer = document.getElementById("chat-container");

  // Get last message's timestamp
  if (chatContainer.children.length !== 0) {
    var messageElements = chatContainer.children;
    var lastMessageTimestamp = parseInt(messageElements[messageElements.length - 1].getAttribute("timestamp"));
  } else {
    var lastMessageTimestamp = 0;
  }

  // Fetch latest messages
  const response = await fetch("/get_messages", {
    method: "POST",
    body: JSON.stringify({
      count: messagesCount,
      after: lastMessageTimestamp
    }),
  });

  // Get Messages
  const messages = await response.json();

  if (messages.err !== undefined) {
    alert("Error: " + messages.err);
    return;
  }

  // Append messages
  for (const msg of messages) {
    if (msg.type === "text") {
      const content = await fetch("/get_message_content/" + msg.hash).then((res) => res.text());
      addMessage(msg.timestamp, msg.author, content, "text");
    } else {
      addMessage(msg.timestamp, msg.author, msg.hash, msg.type, msg.filename);
    }
  }
}