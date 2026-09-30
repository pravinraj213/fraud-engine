const paths = {
  shield: "M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3Z M8.5 12l2.5 2.5 4.5-5",
  queue: "M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z",
  rules: "M4 7h16 M4 17h16 M8 4v6 M16 14v6",
  play: "m9 5 11 7-11 7V5Z M4 5v14",
  arrow: "M5 12h14 m-5-5 5 5-5 5",
  chevron: "m9 5 7 7-7 7",
  refresh:
    "M20 7v5h-5 M4 17v-5h5 M6 7a7 7 0 0 1 12-1l2 3 M4 15l2 3a7 7 0 0 0 12-1",
  search: "M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6",
  download: "M12 3v12 m-5-5 5 5 5-5 M4 16v5h16v-5",
  flag: "M5 21V4 m0 0c5-4 9 4 14 0v10c-5 4-9-4-14 0",
  check: "m5 12 4 4L19 6",
  activity: "M3 12h4l3-8 4 16 3-8h4",
  clock: "M12 8v5l3 2 M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18",
  globe:
    "M3 12h18 M12 3c-6 5-6 13 0 18 6-5 6-13 0-18Z M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18",
  alert: "m12 3 10 18H2L12 3Z M12 9v5 M12 17v.1",
  menu: "M4 6h16 M4 12h16 M4 18h16",
  user: "M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M4 21v-3a8 5 0 0 1 16 0v3",
};
export default function Icon({ name, size = 20, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <path d={paths[name] || paths.shield} />
    </svg>
  );
}
