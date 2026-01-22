import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "react-router-dom";
import { KeyIcon } from "@heroicons/react/24/outline";
import { blackfishApiURL } from "@/config";

export default function LoginPage() {
  const [token, setToken] = useState("");
  const [errorMessage, setErrorMessage] = useState(null);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (searchParams.get("success") === "false") {
      setErrorMessage("Authentication failed. Please try again.");
    }
  }, [searchParams]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setErrorMessage(null);

    try {
      const res = await fetch(`${blackfishApiURL}/api/login?token=${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      if (res.redirected) {
        const successParam = new URL(res.url).searchParams.get("success");
        if (successParam === "false") {
          throw new Error("Invalid token");
        }
        window.location.href = res.url;
      }
    } catch (err) {
      setErrorMessage("Login failed. Please try again.");
      console.error(err);
    }
  };

  return (
    <Suspense>
      <div className="flex items-center justify-center mt-96">
        <form onSubmit={handleLogin} className="py-3 px-1 w-2/5">
          <div className="flex items-center justify-center mb-4">
            <input
              type="text"
              placeholder="Enter authentication token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="w-full rounded-none rounded-l-md border-0 py-1.5 pl-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6"
              style={{ boxSizing: "border-box" }}
            />
            <button
              type="submit"
              className="relative -ml-px inline-flex items-center gap-x-1.5 rounded-r-md px-3 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
              style={{ boxSizing: "border-box", height: "100%" }}
            >
              <KeyIcon className="h-5 w-5" />
              Login
            </button>
          </div>

          {errorMessage && (
            <p className="text-red-500 text-center mb-4">{errorMessage}</p>
          )}
        </form>
      </div>
    </Suspense>
  );
}
