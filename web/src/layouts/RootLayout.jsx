import { Outlet, useLocation } from "react-router-dom";
import { ProfileProvider } from "@/components/ProfileSelect";
import NavbarLight from "@/components/NavbarLight";

function RootLayout() {
  const location = useLocation();

  const task = location.pathname.split('/')[1] || 'dashboard';
  const isLoginPage = location.pathname.endsWith('login');

  return (
    <ProfileProvider>
      <div className="font-sans">
        <NavbarLight task={task} />
        {isLoginPage ? (
          <Outlet />
        ) : (
          <section className="mb-4 mt-6 ml-8 mr-8">
            <Outlet />
          </section>
        )}
      </div>
    </ProfileProvider>
  );
}

export default RootLayout;
