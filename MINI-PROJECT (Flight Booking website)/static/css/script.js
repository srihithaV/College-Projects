document.addEventListener("DOMContentLoaded", function () {
    const oneWayBtn = document.getElementById("oneWayBtn");
    const roundTripBtn = document.getElementById("roundTripBtn");
    const arrivalDateGroup = document.getElementById("arrivalDateGroup");

    oneWayBtn.addEventListener("click", function () {
        oneWayBtn.classList.add("active");
        roundTripBtn.classList.remove("active");
        arrivalDateGroup.style.display = "none";
    });

    roundTripBtn.addEventListener("click", function () {
        roundTripBtn.classList.add("active");
        oneWayBtn.classList.remove("active");
        arrivalDateGroup.style.display = "block";
    });

    // Initially hide arrival date for one-way
    arrivalDateGroup.style.display = "none";
});