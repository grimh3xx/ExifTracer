**ExifTracer**

📸 **Analyzes images, extracts EXIF data, GPS location and displays full address.**

----

📌 **Functionalities**

📍 **Extract GPS coordinates — retrieve latitude and longitude directly from images.**
🏠 **Reverse geocoding — convert coordinates into full addresses (street, city, state, country, ZIP/CEP).**
🗺️ **Interactive map generation — automatically create maps with Folium for easy visualization.**
📂 **Batch analysis — support for analyzing multiple images at once.**
🎨 **Modern terminal interface — clean and elegant UI powered by Rich.**

---

**Instalation**

```bash
git clone <seu-repo>
cd ExifTracer
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

**Example to execution**

```bash
~/ExifTracer ❯ /home/youruser/ExifTracer/.venv/bin/python /home/youruser/ExifTracer/main.py
    
╭────────────── ExifTracer ───────────────╮                                          
│                                         │                                          
│  [*] ExifTracer Interactive Panel [*]   │                                          
│ [+] Escolha uma opção para começar: [+] │                                          
│                                         │                                          
│       [1] 🖼️  Analisar uma imagem       │                                          
│   [2] 📂  Analisar múltiplas imagens    │                                          
│              [0] ❌  Sair               │                                          
│                                         │                                          
╰─────────────────────────────────────────╯                                          
Digite sua escolha ➜ 1
Digite o caminho da imagem ➜ /home/youruser/Documents/test_gps.jpg 
Você escolheu analisar a imagem ➜ /home/youruser/Documents/test_gps.jpg
                      Dados de Geolocalização                      
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Campo     ┃ Valor                                               ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ latitude  │ 43.468243333330555                                  │
│ longitude │ 11.880171666638889                                  │
│ address   │ Via della Chiassaia, Arezzo, Toscana, 52100, Italia │
│ road      │ Via della Chiassaia                                 │
│ suburb    │ None                                                │
│ city      │ Arezzo                                              │
│ state     │ Toscana                                             │
│ country   │ Italia                                              │
│ postcode  │ 52100                                               │
└───────────┴─────────────────────────────────────────────────────┘
Mapa salvo em map.html 
```

**Example with Images**
![Banner](/home/0xBl4ckn3t/Screenshots)
![Terminal](/home/0xBl4ckn3t/Screenshots)
![Mapa Interativo](/home/0xBl4ckn3t/Screenshots)



**View of the map:**

**Open the map.html file in the browser to see the location:**
```bash
@ firefox map.html   # Linux
@ start map.html     # Windows
@ open map.html      # macOS


```


