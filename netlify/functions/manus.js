// هذا هو العقل المدبر "مانوس"
// This is the "Manus" mastermind function
 
export default async (req, context) => {
  // أولاً، نتأكد أن الطلب صحيح
  if (req.method !== 'POST') {
    return new Response("Method Not Allowed", { status: 405 });
  }

  let productData;
  try {
    productData = await req.json();
  } catch (error) {
    return new Response("Bad Request: Invalid JSON", { status: 400 });
  }

  const { productName, productNotes } = productData;

  if (!productName) {
    return new Response("Bad Request: productName is required", { status: 400 });
  }

  // هنا تبدأ شخصية مانوس
  const manusPrompt = `
    أنت مانوس، مساعد تسويق ذكي وخبير في صياغة المحتوى الإعلاني الجذاب لمنصات التواصل الاجتماعي.
    مهمتك هي استلام معلومات منتج وتحويلها إلى منشور إعلاني إبداعي ومقنع.

    معلومات المنتج كالتالي:
    - اسم المنتج: "${productName}"
    - ملاحظات إضافية من المستخدم: "${productNotes || 'لا توجد ملاحظات'}"

    المطلوب منك:
    1.  اكتب نصًا إعلانيًا قصيرًا (جملتين إلى ثلاث جمل) باللهجة السعودية، يبرز أهمية المنتج ويثير فضول القارئ.
    2.  استخدم 2-3 إيموجي مناسبة وذات صلة في بداية النص أو وسطه.
    3.  اختم المنشور بسؤال ذكي ومفتوح (Call to Action) لتشجيع المتابعين على التفاعل والتعليق.
    4.  اقترح 3 إلى 5 هاشتاجات قوية ومناسبة للمنتج والسوق السعودي.

    قم بإرجاع الرد بصيغة JSON فقط، بدون أي نصوص إضافية، بالشكل التالي:
    {
      "postText": "النص الإعلاني الذي كتبته هنا مع الإيموجي والسؤال",
      "hashtags": ["#هاشتاق1", "#هاشتاق2", "#هاشتاج3"]
    }
  `;

  // الآن، نتحدث مع محرك OpenAI
  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`
      },
      body: JSON.stringify({
        model: "gpt-4o", // استخدام أحدث موديل
        messages: [{ role: "user", content: manusPrompt }],
        response_format: { type: "json_object" } // نطلب منه إرجاع الرد كـ JSON
      })
    });

    const result = await response.json();
    
    if (!response.ok) {
        // إذا حدث خطأ من OpenAI
        console.error("OpenAI API Error:", result);
        return new Response(JSON.stringify(result), { status: response.status });
    }

    const manusResponse = JSON.parse(result.choices[0].message.content);

    // نرجع الإجابة النهائية من مانوس
    return new Response(JSON.stringify(manusResponse), {
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error("Internal Server Error:", error);
    return new Response("Internal Server Error", { status: 500 });
  }
};
