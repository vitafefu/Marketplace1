document.getElementById('year').textContent = new Date().getFullYear();

// ================= Модалка =====================
const modal = document.getElementById('auth-modal');
const btn = document.getElementById('auth-btn');
const span = modal.querySelector('.close');

btn.onclick = () => modal.style.display = 'block';
span.onclick = () => modal.style.display = 'none';
window.onclick = e => { if(e.target == modal) modal.style.display='none'; }

// ================= Меню =====================
const menuBtn = document.querySelector('.menu-btn');
const headerRight = document.querySelector('.header-right');
const buttons = document.querySelectorAll('.header-right > *');

menuBtn.addEventListener('click', () => {
    headerRight.classList.toggle('active');

    // Задержка для поэтапного появления
    buttons.forEach((btn, i) => {
        btn.style.transitionDelay = headerRight.classList.contains('active') ? `${i*0.1}s` : `0s`;
    });
});
