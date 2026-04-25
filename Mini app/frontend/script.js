const API = "";

const $ = id => document.getElementById(id);

async function submitJob() {

  const raw     = $("numbers-input").value.trim();
  const numbers = raw.split(/[\s,]+/).map(Number).filter(v => !isNaN(v));
  if (!numbers.length) { alert("Please enter at least one valid number."); return; }

  const operation = $("op-select").value;

  $("status").textContent  = "Submitting job...";
  $("results").innerHTML   = "";
  $("submit-btn").disabled = true;

  try {
    const res = await fetch(`${API}/start-job`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ numbers, operation }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Server error");
    }

    const { job_id, total_tasks } = await res.json();
    $("status").textContent = `Job submitted. ${total_tasks} tasks running in parallel. Polling for results...`;

    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await fetch(`${API}/job-status/${job_id}`);
        const data      = await statusRes.json();

        if (data.status === "success") {
          clearInterval(pollInterval);
          $("status").textContent  = `All ${data.results.length} tasks finished successfully.`;
          $("submit-btn").disabled = false;
          renderResults(data.results, data.summary);

        } else if (data.status === "failed") {
          clearInterval(pollInterval);
          $("status").textContent  = `Job failed: ${data.error}`;
          $("submit-btn").disabled = false;

        } else {
          $("status").textContent = `Status: ${data.status}... still waiting.`;
        }

      } catch (e) {
        clearInterval(pollInterval);
        $("status").textContent  = `Polling error: ${e.message}`;
        $("submit-btn").disabled = false;
      }
    }, 800);

  } catch (e) {
    $("status").textContent  = `Error: ${e.message}`;
    $("submit-btn").disabled = false;
  }
}

function renderResults(results, summary) {
  const container = $("results");
  const list = results.map(r => `<li>${r.operation}(${r.input}) = ${r.output}</li>`).join("");
  container.innerHTML = `
    <h3>Results</h3>
    <ul>${list}</ul>
    <h3>Summary</h3>
    <p>Count: ${summary.count}</p>
    <p>Total: ${summary.total}</p>
    <p>Average: ${summary.average.toFixed(2)}</p>
    <p>Min: ${summary.min}</p>
    <p>Max: ${summary.max}</p>
  `;
}