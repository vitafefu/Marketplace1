document.addEventListener("DOMContentLoaded", () => {
  const reviewsList = document.getElementById("reviews-list");
  const createForm = document.getElementById("review-create-form");
  const toast = document.getElementById("review-toast");
  const reviewFormWrapper = document.getElementById("review-form-wrapper");
  const alreadyMessage = document.getElementById("review-already-message");
  const reviewsEmpty = document.getElementById("reviews-empty");

  if (!reviewsList) return;

  const getCookie = (name) => {
    const match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return match ? match.pop() : "";
  };

  const showToast = (message) => {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("is-visible");
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => {
      toast.classList.remove("is-visible");
    }, 2500);
  };

  const clearErrors = (form) => {
    if (!form) return;
    form.querySelectorAll(".form-error").forEach((el) => {
      el.textContent = "";
    });
  };

  const renderErrors = (form, errors) => {
    if (!form || !errors) return;
    Object.entries(errors).forEach(([field, messages]) => {
      const container = form.querySelector(`[data-error-for="${field}"]`);
      if (container) {
        container.textContent = (messages || []).join(" ");
      }
    });
  };

  const updateSummary = (avgRating, reviewsCount) => {
    const avgValue = document.getElementById("avg-rating-value");
    const countValue = document.getElementById("reviews-count");
    const starsWrap = document.getElementById("avg-rating-stars");

    if (avgValue) avgValue.textContent = `${avgRating}/5`;
    if (countValue) countValue.textContent = reviewsCount;

    if (starsWrap) {
      const rounded = Math.round(Number(avgRating) || 0);
      let stars = "";
      for (let i = 1; i <= 5; i += 1) {
        stars += i <= rounded ? "⭐" : "☆";
      }
      starsWrap.textContent = stars;
    }
  };

  const ensureEmptyState = () => {
    const hasAnyCards = !!reviewsList.querySelector("[data-review-id]");
    if (!hasAnyCards) {
      if (!document.getElementById("reviews-empty")) {
        const empty = document.createElement("p");
        empty.id = "reviews-empty";
        empty.style.textAlign = "center";
        empty.style.color = "#777";
        empty.textContent = "Отзывов пока нет";
        reviewsList.appendChild(empty);
      }
    }
  };

  const insertReviewHtml = (html) => {
    const empty = document.getElementById("reviews-empty");
    if (empty) empty.remove();
    reviewsList.insertAdjacentHTML("afterbegin", html);
  };

  const replaceReviewHtml = (reviewId, html) => {
    const card = reviewsList.querySelector(`[data-review-id="${reviewId}"]`);
    if (card) card.outerHTML = html;
  };

  const removeReview = (reviewId) => {
    const card = reviewsList.querySelector(`[data-review-id="${reviewId}"]`);
    if (card) card.remove();
    ensureEmptyState();
  };

  const showCreateForm = () => {
    if (reviewFormWrapper) reviewFormWrapper.style.display = "block";
    if (alreadyMessage) alreadyMessage.style.display = "none";
    if (createForm) createForm.reset();
  };

  const hideCreateForm = () => {
    if (reviewFormWrapper) reviewFormWrapper.style.display = "none";
    if (alreadyMessage) alreadyMessage.style.display = "block";
  };

  const handleResponse = async (response, form, onSuccess) => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) {
      clearErrors(form);
      renderErrors(form, data.errors);
      showToast("Не удалось выполнить действие");
      return null;
    }
    onSuccess(data);
    return data;
  };

  // CREATE
  if (createForm) {
    createForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearErrors(createForm);

      const url = createForm.dataset.apiUrl || createForm.action;
      const formData = new FormData(createForm);

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Accept": "application/json",
          },
          body: formData,
        });

        await handleResponse(response, createForm, (data) => {
          insertReviewHtml(data.html);
          updateSummary(data.avg_rating, data.reviews_count);
          hideCreateForm();
          showToast("Спасибо за отзыв!");
        });
      } catch (error) {
        showToast("Ошибка сети при отправке отзыва");
      }
    });
  }

  // CLICK HANDLERS (edit toggle + delete)
  reviewsList.addEventListener("click", async (event) => {
    const editBtn = event.target.closest(".review-edit-toggle");
    if (editBtn) {
      const reviewId = editBtn.dataset.reviewId;
      const form = reviewsList.querySelector(`.review-edit-form[data-review-id="${reviewId}"]`);
      if (form) {
        form.style.display = form.style.display === "none" ? "block" : "none";
      }
      return;
    }

    const deleteBtn = event.target.closest(".review-delete-btn");
    if (!deleteBtn) return;

    event.preventDefault();
    if (!window.confirm("Удалить отзыв?")) return;

    const reviewId = deleteBtn.dataset.reviewId;
    const url = deleteBtn.dataset.apiUrl || deleteBtn.getAttribute("href");

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "Accept": "application/json",
        },
      });

      await handleResponse(response, null, (data) => {
        removeReview(reviewId);
        updateSummary(data.avg_rating, data.reviews_count);
        showCreateForm(); // <-- ВАЖНО: после удаления снова разрешаем оставить отзыв
        showToast("Отзыв удалён");
      });
    } catch (error) {
      showToast("Ошибка сети при удалении отзыва");
    }
  });

  // UPDATE
  reviewsList.addEventListener("submit", async (event) => {
    const form = event.target.closest(".review-edit-form");
    if (!form) return;

    event.preventDefault();
    clearErrors(form);

    const url = form.dataset.apiUrl || form.action;
    const formData = new FormData(form);

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "Accept": "application/json",
        },
        body: formData,
      });

      await handleResponse(response, form, (data) => {
        replaceReviewHtml(form.dataset.reviewId, data.html);
        updateSummary(data.avg_rating, data.reviews_count);
        showToast("Отзыв обновлён");
      });
    } catch (error) {
      showToast("Ошибка сети при обновлении отзыва");
    }
  });
});
