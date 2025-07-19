// static/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {

    // --- Monthly Sales Bar Chart ---
    const monthlySalesCtx = document.getElementById('monthlySalesChart');
    if (monthlySalesCtx && typeof monthlySalesData !== 'undefined') {
        const labels = Object.keys(monthlySalesData).sort(); // Sort months chronologically
        const data = labels.map(key => monthlySalesData[key]);

        new Chart(monthlySalesCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Monthly Sales Revenue ($)',
                    data: data,
                    backgroundColor: 'rgba(135, 206, 235, 0.7)', // var(--color-primary-light-blue)
                    borderColor: 'rgba(70, 130, 180, 1)', // var(--color-text-blue)
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Revenue ($)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Month'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Last 6 Months Sales'
                    }
                }
            }
        });
    }

    // --- Sales by Category Pie Chart ---
    const categorySalesCtx = document.getElementById('categorySalesPieChart');
    if (categorySalesCtx && typeof categorySalesData !== 'undefined') {
        const labels = Object.keys(categorySalesData);
        const data = Object.values(categorySalesData);

        const backgroundColors = [
            '#87CEEB', '#ADD8E6', '#4682B4', '#5F9EA0', '#B0C4DE', // Shades of light blue
            '#F08080', '#FFA07A', '#FFDAB9', '#DAA520', '#C0C0C0' // Fallback/more colors
        ];

        new Chart(categorySalesCtx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sales by Category',
                    data: data,
                    backgroundColor: backgroundColors.slice(0, labels.length),
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    title: {
                        display: true,
                        text: 'Top 5 Product Categories by Sales'
                    }
                }
            }
        });
    }

    // --- Daily Sales Line Graph ---
    const dailySalesCtx = document.getElementById('dailySalesLineChart');
    if (dailySalesCtx && typeof dailySalesData !== 'undefined') {
        const sortedDates = Object.keys(dailySalesData).sort();
        const data = sortedDates.map(date => dailySalesData[date]);

        new Chart(dailySalesCtx, {
            type: 'line',
            data: {
                labels: sortedDates,
                datasets: [{
                    label: 'Daily Sales Revenue ($)',
                    data: data,
                    fill: true,
                    borderColor: 'rgba(70, 130, 180, 1)', /* var(--color-text-blue) */
                    backgroundColor: 'rgba(135, 206, 235, 0.2)', /* var(--color-primary-light-blue) transparent */
                    tension: 0.3, /* Smooth the line */
                    pointBackgroundColor: 'rgba(70, 130, 180, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(70, 130, 180, 1)',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Revenue ($)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        },
                        // You might want to format dates better here if needed
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Daily Sales Trends (Last 30 Days)'
                    }
                }
            }
        });
    }
});
