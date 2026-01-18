#!/bin/bash

# إيقاف نسخ البوت الإضافية على Railway
# استخدم هذا الأمر من Railway CLI

echo "⚠️ خطوات إيقاف النسخ الإضافية على Railway:"
echo ""
echo "الخطوة 1: افتح Railway Dashboard"
echo "  URL: https://railway.app"
echo ""
echo "الخطوة 2: اختر مشروع TelegramStoreBot"
echo ""
echo "الخطوة 3: انظر إلى قسم Deployments"
echo "  - يجب أن ترى نسخة واحدة فقط مشغلة (Status: Running)"
echo "  - إذا رأيت أكثر من واحدة، اضغط على الإضافية واختر 'Remove'"
echo ""
echo "الخطوة 4: تأكد من أن Replicas = 1"
echo "  - اذهب إلى Settings"
echo "  - تأكد من Replicas = 1"
echo ""
echo "الخطوة 5: أعد تشغيل البوت"
echo "  - اضغط على 'Redeploy'"
echo ""
echo "✅ بعد ذلك جرب إضافة صورة!"
