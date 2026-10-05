# lineend

检测与转换文本文件的行尾符（CRLF / LF / 孤立 CR）。纯标准库，纯本地。

## 安装

零依赖，把目录放到 `PATH` 或直接用：

```bash
python3 -m lineend detect file.txt
```

## 用法

```bash
# 检测
lineend detect README.md
lineend detect --json README.md
cat file.txt | lineend detect --stdin

# 转换（原地）
lineend to-lf file.txt            # 转为 LF（Unix/macOS 风格）
lineend to-crlf file.txt          # 转为 CRLF（Windows 风格）
lineend to-lf file.txt --backup   # 先备份为 file.txt.bak
lineend to-lf file.txt --dry-run  # 只看会发生什么，不写入
```

示例输出：

```
===== 行尾检测：examples/mixed.txt =====
  CRLF（\r\n）：3
  LF  （\n）  ：2
  CR  （\r）  ：1
  结论：混合行尾
```

## 设计取舍

- **二进制安全**：以字节流方式读取，逐字节计数，不受文本模式
  universal newlines 干扰。含 NUL 字节的文件会标记"可能是二进制"；
  `detect` 只警告不崩溃，`to-lf`/`to-crlf` 直接拒绝转换——
  文本工具不碰二进制文件，这是故意的。
- **孤立 CR**：经典 Mac OS（9 及以前）的行尾，现在极其罕见；
  能检测、能转换，但日常基本碰不到。
- 转换逻辑是"先归一化为 LF，再按目标重组"，混合行尾一次转干净。

## 已知局限

- 整个文件读入内存；GB 级文件会慢（日常文本文件没问题）。
- 只处理三种行尾；EBCDIC 之类的古董编码不在范围内。
- 检测的是字节特征，不判断"这个文件该用什么行尾"——那是你的决定。

## 许可证

MIT，Copyright (c) 2026 ljiang9。
