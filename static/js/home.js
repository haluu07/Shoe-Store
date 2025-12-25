// Điều khiển slider hero
let currentSlide = 0;
const slides = document.querySelectorAll('.hero-slide');
const totalSlides = slides.length;

function showSlide(index) {
    slides.forEach((slide, i) => {
        slide.classList.remove('active');
        if (i === index) {
            slide.classList.add('active');
        }
    });
}

function moveSlide(step) {
    currentSlide = (currentSlide + step + totalSlides) % totalSlides;
    showSlide(currentSlide);
}

// Điều khiển cuộn sản phẩm
function scrollProducts(direction) {
    const container = document.getElementById('productContainer');
    if (container) {
        const scrollAmount = 300;
        container.scrollLeft += direction * scrollAmount;
    } else {
        console.error("Không tìm thấy productContainer");
    }
}

// Chạy sau khi DOM được tải
document.addEventListener('DOMContentLoaded', () => {
    // Hiển thị slide đầu tiên cho hero-slider
    if (totalSlides > 0) {
        showSlide(currentSlide);
    }

    // Tự động chuyển slide mỗi 3 giây
    setInterval(() => {
        moveSlide(1);
    }, 3000);

    // Tự động phát video khi trang tải
    const categories = document.querySelectorAll('.category');
    categories.forEach(category => {
        const video = category.querySelector('.category-video');
        if (video) {
            // Tự động phát video khi trang tải
            video.play().catch(error => {
                console.error("Lỗi khi tự động phát video:", error);
            });
        }
    });
});