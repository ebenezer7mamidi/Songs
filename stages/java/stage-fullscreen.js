var intfadein = 300;
var intfadeout = 300;

window.OpenLP = {
    allowedLangs: [],
    fontCache: new Map(),   // cache for autoScaleText

    myWebSocket: function () {
        const host = window.location.hostname;
        const websocket_port = 4317;

        const ws = new WebSocket(`ws://${host}:${websocket_port}`);
        ws.onmessage = (event) => {
            const reader = new FileReader();
            reader.onload = () => {
                const data = JSON.parse(reader.result.toString()).results;

                OpenLP.curStatus = 'live';
                if (data.theme) OpenLP.curStatus = 'theme';
                if (data.display) OpenLP.curStatus = 'display';
                if (data.blank) OpenLP.curStatus = 'blank';
                OpenLP.curStatus = 'live'; // overriding - always live

                if (OpenLP.currentItem != data.item || OpenLP.currentService != data.service) {
                    OpenLP.currentItem = data.item;
                    OpenLP.currentService = data.service;
                    OpenLP.loadSlides();
                } else if (OpenLP.currentSlide != data.slide) {
                    OpenLP.currentSlide = parseInt(data.slide, 10);
                    OpenLP.updateSlide();
                } else {
                    OpenLP.loadService();
                }
            };
            reader.readAsText(event.data);
        };
    },

    loadService: function () {
        $.getJSON("/api/v2/service/items", function (data) {
            OpenLP.serviceTitle = "";
            data.forEach(function (item) {
                if (item.selected) {
                    OpenLP.currentItem = item;
                    OpenLP.curPlugin = item.plugin;

                    if (OpenLP.curPlugin === 'bibles' && OpenLP.curStatus === 'live') {
                        // Trim title for Bible: keep only "Book Chapter:Verse"
                        const match = item.title.match(/^([^\s,]+ \d+:\d+(-\d+)?)/);
                        OpenLP.serviceTitle = match ? match[1] : item.title;
                    } else {
                        OpenLP.serviceTitle = item.title; // Ebby show title for songs also
                    }

                    OpenLP.updateSlide();
                }
            });
        });
    },

    loadSlides: function () {
        $.getJSON("/api/v2/controller/live-items", function (data) {
            OpenLP.currentSlides = data.slides;
            OpenLP.currentSlide = 0;
            $.each(data.slides, function (idx, slide) {
                if (slide.selected)
                    OpenLP.currentSlide = idx;
            });
            OpenLP.loadService();
        });
    },

    updateSlide: function () {
        const slide = OpenLP.currentSlides[OpenLP.currentSlide];
        let text = slide.html || slide.title;

        text = text.replace(/\n/g, "<br/>");
        if (OpenLP.curtext !== text) {
            OpenLP.curtext = text;
            const disText = OpenLP.processOpenLPText(OpenLP.curtext);

            $("#currentslide").fadeOut(intfadeout, function () {
                $("#currentslide").html(disText);
                const wrapper = document.querySelector("#currentslide .slide-wrapper");
                OpenLP.autoScaleText(wrapper);
            });
            $("#currentslide").fadeIn(intfadein);
        }
    },

    processOpenLPText: function (rawHtml) {
        // --- Read allowed languages and orientation from HTML ---
        const scriptLang = document.querySelector('script[data-allowed-langs]');
        OpenLP.allowedLangs = scriptLang ? scriptLang.getAttribute('data-allowed-langs').split(',').map(l => 'lang-' + l) : ['lang-eng'];

        const scriptOrient = document.querySelector('script[data-orientation]');
        const orientation = scriptOrient ? scriptOrient.getAttribute('data-orientation') : 'horizontal';

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = rawHtml;

        // Select language divs that match allowedLangs
        let langDivs = Array.from(tempDiv.querySelectorAll('div[class^="lang-"]'))
            .filter(div => OpenLP.allowedLangs.includes(div.className));

        const wrapper = document.createElement('div');
        wrapper.classList.add('slide-wrapper', orientation);

        const textBlock = document.createElement('div');
        textBlock.classList.add('text-block');

        // Service title on top
        if (OpenLP.serviceTitle) {
            const label = document.createElement('label');
            label.classList.add('service-title');
            label.textContent = OpenLP.serviceTitle;
            textBlock.appendChild(label);
        }

        const textContent = document.createElement('div');
        textContent.classList.add('text-content');

        if (langDivs.length === 0) {
            const defaultDiv = document.createElement('div');
            defaultDiv.classList.add('lang-default');
            defaultDiv.innerHTML = rawHtml;
            textContent.appendChild(defaultDiv);
        } else {
            langDivs.forEach(div => textContent.appendChild(div));
        }

        textBlock.appendChild(textContent);
        wrapper.appendChild(textBlock);

        return wrapper.outerHTML;
    },

    autoScaleText: function (wrapper) {
        if (!wrapper) return;

        const textContent = wrapper.querySelector('.text-content');
        if (!textContent) return;

        const langDivs = Array.from(textContent.children).filter(c => c.textContent.trim() !== '');
        const isVertical = wrapper.classList.contains('vertical');
        const multiLang = langDivs.length > 1;

        requestAnimationFrame(() => {
            const availableWidth = textContent.clientWidth;
            const availableHeight = textContent.clientHeight;

            langDivs.forEach(child => {
                const key = child.textContent.length + "|" + isVertical + "|" + multiLang + "|" + availableWidth + "x" + availableHeight;
                if (OpenLP.fontCache.has(key)) {
                    child.style.fontSize = OpenLP.fontCache.get(key) + "px";
                    return;
                }

                // Binary search fit
                let min = 10;
                let max = Math.floor(Math.min(availableWidth, availableHeight) * 0.8);
                let best = min;

                while (min <= max) {
                    const mid = Math.floor((min + max) / 2);
                    child.style.fontSize = mid + "px";

                    if (child.scrollHeight <= availableHeight && child.scrollWidth <= availableWidth) {
                        best = mid;
                        min = mid + 1;
                    } else {
                        max = mid - 1;
                    }
                }

                // Apply vertical + multi-lang reduction
                if (isVertical && multiLang) {
                    best = Math.floor(best * 0.7);
                }

                child.style.fontSize = best + "px";
                OpenLP.fontCache.set(key, best);
            });
        });
    },

    initBackground: function () {
        const canvas = document.createElement("canvas");
        canvas.id = "bg-canvas";
        document.body.prepend(canvas);

        const ctx = canvas.getContext("2d");
        let particles = [];

        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resizeCanvas();
        window.addEventListener("resize", resizeCanvas);

        // fewer particles for OBS performance
        for (let i = 0; i < 20; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                r: Math.random() * 2 + 1,
                d: Math.random() * 0.5
            });
        }

        function drawBackground() {
            const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
            gradient.addColorStop(0, "#1a2a6c");
            gradient.addColorStop(0.5, "#16222A");
            gradient.addColorStop(1, "#3A6073");

            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
            ctx.beginPath();
            for (let i = 0; i < particles.length; i++) {
                let p = particles[i];
                ctx.moveTo(p.x, p.y);
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2, true);
            }
            ctx.fill();
            updateParticles();
        }

        function updateParticles() {
            for (let i = 0; i < particles.length; i++) {
                let p = particles[i];
                p.y += p.d;
                if (p.y > canvas.height) {
                    p.y = 0;
                    p.x = Math.random() * canvas.width;
                }
            }
        }

        function animate() {
            drawBackground();
            requestAnimationFrame(animate);
        }
        animate();
    }
};

// Initialize
$.ajaxSetup({
    cache: false
});
OpenLP.myWebSocket();
document.addEventListener('DOMContentLoaded', function () {
    OpenLP.initBackground();
});
