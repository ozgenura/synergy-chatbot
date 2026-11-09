# Synergy

A-Lab Chatbot Casting görevi için geliştirilmiş, kişiliği olan bir RAG chatbotu. Kurgusal Mars Turizm şirketi hakkındaki soruları yalnızca bilgi dosyasına dayanarak yanıtlar. Tamamen lokal çalışır, API anahtarı gerekmez.

## Karakter

Karakter, tahmin oyunu bitene kadar gizli. Birkaç soru sorun, kim olduğunu siz bulun. Demodan sonra bu bölüm doldurulacak.

Sürprizi korumak istiyorsanız `persona.py` dosyasını ve testleri okumayın, uygulamadaki "Paneli göster" anahtarını da en sona bırakın.

## Özellikler

- **Kaynağa bağlı cevaplar:** Şirket soruları `data/mars_turizm.txt` dosyasından yanıtlanır. Dosyada olmayan bilgi için "Bu veri elimdeki dokümanda yok." der.
- **Konuşma geçmişi:** Takip soruları ve kısa tepkiler önceki konuşmaya bağlanır.
- **Oturumlar arası hafıza:** Dokümanda bulunamayan sorular `memory/open_gaps.json` dosyasında tutulur. Bu dosya bilgi kaynağı değildir ve repoya girmez; uygulamadaki "Hafızayı sıfırla" düğmesiyle temizlenir.
- **İkinci görünüm:** Kenar çubuğundaki "Paneli göster" anahtarı, karakterin kendi dünyasını açar. Tahminler bitene kadar kapalı tutulmalıdır.

## Mimari

| Dosya | Görevi |
|---|---|
| `app.py`, `notebook.py` | Streamlit arayüzü ve ikinci görünüm |
| `rag.py` | Bilgi dosyasını satırlara böler, `bge-m3` embedding ve karakter n-gram TF-IDF ile ilgili satırları seçer |
| `persona.py` | System prompt, soru türü sınıflandırması ve her tura özel talimatlar |
| `llm.py` | Ollama bağlantısı, konuşma geçmişi ve cevap düzeltme döngüsü |
| `meeting.py` | Cevap kontrolleri, oturum metrikleri ve özet |
| `memory.py` | Oturumlar arası açık soru hafızası |
| `page_mascot.py` | Sayfa içi animasyonlu maskot |
| `mascot.py`, `mascot_art.py`, `mascot_state.py` | Masaüstü maskotu (yalnızca Windows), çizimler ve arayüzle iletişim |
| `scripts/` | Retrieval ölçümü, model karşılaştırması ve sohbet testleri |

**Uydurmaya karşı önlemler:**

1. Soru türünü Python belirler ve modele o tura özel talimat verir.
2. Cevaptaki sayılar bilgi dosyasıyla karşılaştırılır.
3. Dosyada olmayan sayı veya prompt sızıntısı varsa cevap bir kez düzelttirilir, yine temiz değilse güvenli cevaba düşülür.

**Bilinen sınırlar:** Sayı kontrolü, dosyada geçen bir sayının yanlış bağlamda kullanılmasını yakalayamaz. Retrieval skorları "dosyada var/yok" ayrımını tek başına yapamaz, bu ayrım modele bırakılmıştır. Bazı takip soruları kaçabilir; örneğin yaş kuralı konuşulduktan sonra gelen "kaç yaşından küçükler?" sorusu yanlışlıkla dosyada yok sayılıyor.

## Çalıştırma

Gereksinimler: Python 3.13, Ollama 0.40+ ve yaklaşık 7 GB boş GPU belleği (RTX 2070 SUPER 8 GB ile denendi).

```bash
ollama pull gemma4:e4b
ollama pull bge-m3
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Farklı bir model denemek için `SYNERGY_MODEL` ortam değişkenini ayarlayın. İlk açılışta model belleğe yüklendiği için bekleme olabilir.

## Test

```bash
python -m pytest
python scripts/check_retrieval.py
python scripts/evaluate_models.py gemma4:e4b
python scripts/evaluate_conversations.py
```

`pytest` modelsiz çalışır. Diğer komutlar için Ollama açık olmalıdır. Masaüstü maskotunun görsel kontrol betikleri (`scripts/preview_mascot.py`, `scripts/check_mascot.py`) ayrıca `pip install pillow` ister.

Otomatik kontroller aranan bilgiyi ve yasak kelimeleri denetler, üslubu ölçmez. Model çıktısı çalıştırmadan çalıştırmaya değişebilir, bu yüzden testler soruları birkaç kez tekrarlar.
