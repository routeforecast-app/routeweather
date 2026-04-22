function LoadingState({ label = "Loading..." }) {
  return (
    <div className="centered-state">
      <div className="spinner" />
      <p>{label}</p>
    </div>
  );
}

export default LoadingState;
