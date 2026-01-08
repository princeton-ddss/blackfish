"use client";

import { Inter } from "next/font/google";
import "./globals.css";
const inter = Inter({ subsets: ["latin"] });
import { usePathname } from 'next/navigation';
import { ProfileProvider } from "./components/ProfileSelect";
import NavbarLight from './components/NavbarLight'
import { basePath } from "./config";
import PropTypes from "prop-types";

function RootLayout({ children }) {
  const pathName = usePathname();

  return (
    <html lang="en">
      <link rel="icon" href={`${basePath}/img/favicon.ico`} sizes="any" />
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              window.__BLACKFISH_CONFIG__ = {
                apiUrl: "http://{{ request.app.state.HOST }}:{{ request.app.state.PORT }}{{ request.app.state.BASE_PATH }}",
                basePath: "{{ request.app.state.BASE_PATH }}"
              };
            `
          }}
        />
      </head>
      <body className={inter.className}>
        <ProfileProvider>
          <NavbarLight task={pathName.slice(1)} />
          {children}
        </ProfileProvider>
      </body>
    </html>
  );
}

RootLayout.propTypes = {
  children: PropTypes.node,
};

export default RootLayout;
