import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

export default async function PortalIndex() {
  const { getToken } = await auth();
  const token = await getToken();

  // We set a default destination
  let destination = "/portal/support";

  try {
    const response = await fetch("http://127.0.0.1:8000/users/me", {
      headers: {
        Authorization: `Bearer ${token}`
      },
      cache: "no-store" 
    });

    if (response.ok) {
      const userData = await response.json();
      if (userData.role === "FACULTY") {
        destination = "/portal/faculty";
      }
    } else {
      console.error("Backend rejected token");
    }

  } catch (error) {
    console.error("Error fetching user role:", error);
  }

  // MUST BE OUTSIDE TRY/CATCH
  redirect(destination);
}