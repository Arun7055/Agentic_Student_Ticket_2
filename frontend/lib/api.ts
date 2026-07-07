const BASE_URL = "https://agentic-student-ticket-2.onrender.com";

export async function fetchDashboardTickets(token: string | null) {
  if (!token) throw new Error("No authentication token provided");

  const response = await fetch(`${BASE_URL}/tickets`, {
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Failed to fetch tickets");
  }

  return response.json();
}

export async function resolveTicket(ticketId: string, token: string, resolutionNote: string = "") {
    const response = await fetch(`${BASE_URL}/tickets/${ticketId}/resolve`, {
      method: "PATCH",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ resolution_note: resolutionNote }),
    });
  
    if (!response.ok) {
      throw new Error("Failed to resolve ticket");
    }
  
    return response.json();
  }