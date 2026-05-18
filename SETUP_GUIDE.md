# 🚀 Render.com Setup Guide - Step by Step

এই গাইড আপনাকে সম্পূর্ণ প্রক্রিয়া বুঝতে সাহায্য করবে।

---

## 📌 Prerequisites (যা আপনার থাকতে হবে)

Before starting, make sure you have:

### 1. **Telegram Bot Token** 🤖
- Telegram এ `@BotFather` কে message করুন
- `/newbot` command দিন
- Bot এর নাম দিন
- Bot token পাবেন (সংরক্ষণ করুন)

**Example:** `123456789:ABCDEFGHijk-qwertyuiop...`

### 2. **আপনার Telegram User ID** 👤
- `@userinfobot` কে message করুন
- আপনার User ID পাবেন
- সংরক্ষণ করুন

**Example:** `123456789`

### 3. **Polygon Wallet & Private Key** 🔐
- MetaMask ব্যবহার করুন
- Polygon network select করুন
- Private key export করুন
- **⚠️ কখনো কাউকে দেবেন না!**

**Example:** `0x1234abcd...` (দীর্ঘ string)

### 4. **Telegram Channel** 📢
- একটি Telegram channel তৈরি করুন
- Bot কে admin যোগ করুন
- Channel link পাবেন

**Example:** `@my_channel` বা `https://t.me/my_channel`

---

## ✅ Step 1: GitHub Repository Ready

✔️ আপনার `polygon-bot` repository ইতিমধ্যে ready আছে!

Files আছে:
- `bot.py` - Main bot code
- `requirements.txt` - Dependencies
- `Procfile` - Render configuration
- `runtime.txt` - Python version
- `.env.example` - Environment template

---

## ✅ Step 2: Render.com এ সাইন আপ করুন

1. Visit: **https://render.com**
2. **Sign up** (GitHub দিয়ে সবচেয়ে সহজ)
3. GitHub account connect করুন

---

## ✅ Step 3: নতুন Web Service Create করুন

### 2.1 Dashboard খুলুন
- Render dashboard এ যান
- বাম পাশে **Dashboard** দেখবেন

### 2.2 New Service তৈরি করুন
```
Dashboard → New + → Web Service
```

### 2.3 GitHub Repository Connect করুন
- **Connect account** ক্লিক করুন
- GitHub authorization দিন
- `polygon-bot` repository select করুন

### 2.4 Service Details Fill করুন

| Field | Value |
|-------|-------|
| **Name** | `polygon-bot` |
| **Region** | Singapore (বা আপনার country) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python bot.py` |
| **Instance Type** | `Free` (বা যা পাওয়া যায়) |

---

## ✅ Step 4: Environment Variables Set করুন

### Important!
Web Service create করার আগেই এটা করতে হবে!

**Dashboard এ:**
```
Environment → Add Environment Variable
```

এই ৭টি variable add করুন:

### 4.1 BOT_TOKEN
```
Key: BOT_TOKEN
Value: 123456789:ABCDEFGHijk-qwertyuiop...
```
(আপনার BotFather এ পাওয়া token)

### 4.2 ADMIN_IDS
```
Key: ADMIN_IDS
Value: 123456789
```
(আপনার User ID)

যদি একাধিক admin থাকে:
```
Value: 123456789,987654321,555666777
```

### 4.3 CHANNEL_ID
```
Key: CHANNEL_ID
Value: @my_channel
```
অথবা numeric ID:
```
Value: -100123456789
```

### 4.4 CHANNEL_LINK
```
Key: CHANNEL_LINK
Value: https://t.me/my_channel
```

### 4.5 PRIVATE_KEY
```
Key: PRIVATE_KEY
Value: 0x1234abcd5678efgh9012ijkl3456mnop...
```
(আপনার Polygon wallet private key)

### 4.6 RPC_URL
```
Key: RPC_URL
Value: https://1rpc.io/matic
```

### 4.7 LOG_CHANNEL (Optional)
```
Key: LOG_CHANNEL
Value: @admin_logs
```
(যেখানে withdrawals log হবে)

---

## ✅ Step 5: Deploy করুন!

### সব Variables set হওয়ার পর:

```
Create Web Service → Deploy
```

**Deploy হতে সময় লাগে:** ⏳ 5-10 minutes

---

## ✅ Step 6: Deployment Verify করুন

### Dashboard এ:
1. আপনার service খুলুন
2. **Logs** tab দেখুন
3. এই message খুঁজুন:
```
Bot started!
```

### ✅ Success!
Bot এখন 24/7 চলছে!

---

## 🧪 Test করুন

Bot তৈরি হওয়ার পর:

1. Telegram এ আপনার bot search করুন
2. `/start` command দিন
3. Bot respond করবে
4. Channel join করুন
5. `/admin` command দিন (admin হলে)

---

## 🔴 সমস্যা হলে?

### Problem: Bot respond করছে না
**Solution:**
- Logs check করুন (Render dashboard → Logs)
- `BOT_TOKEN` correct কিনা দেখুন
- সব variables set আছে কিনা চেক করুন

### Problem: Deployment failed
**Solution:**
- Logs পড়ুন - কী error আছে
- `requirements.txt` check করুন
- GitHub repo sync করুন

### Problem: Withdrawal fail হচ্ছে
**Solution:**
- `PRIVATE_KEY` correct কিনা চেক করুন
- Wallet এ MATIC আছে কিনা (gas fee এর জন্য)
- RPC URL working কিনা

---

## 📞 কোনো প্রশ্ন?

সব কিছু এখানে ব্যাখ্যা করা আছে।
প্রয়োজনে আবার পড়ুন!

---

## ✨ এখানেই শেষ!

**আপনার bot এখন Render.com এ live! 🎉**

Enjoy! 🚀
