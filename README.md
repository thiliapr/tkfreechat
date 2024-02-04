# TkFreeChat

[![GitHub License](https://img.shields.io/github/license/thiliapr/tkfreechat)](https://github.com/thiliapr/tkfreechat/blob/master/LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/thiliapr/tkfreechat)](https://github.com/thiliapr/tkfreechat/stargazers)

Languages: [English](./README.md) | [简体中文](./README.zh-cn.md)

## Introduction

**TkFreeChat** is an open-source chat server software released under the **AGPLv3 or higher** license.

## Features

1. Simple chat server supporting multi-user conversations.
2. No registration required to join the chat.

## Drawbacks

1. Each message requires re-downloading the last 15 chat messages, which can strain the server (implemented in `chat.js`).
2. Lack of user authentication; anyone can use any username (due to the complexity of public-private key pairs for regular users).
3. The interface is not optimized for PC usage (CSS expertise needed for better PC compatibility).

## Recommendations

- Consider using **ngrok** for local network tunneling or set up a dedicated server.

Feel free to contribute and improve the project!
