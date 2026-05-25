function DocumentarDano({ contId, token, onDone }) {
  const [desc, setDesc] = React.useState("");
  async function reportar() {
    await api(`/contrataciones/${contId}/irregularidad`, {
      method: "POST", token, body: { descripcion: desc },
    });
    setDesc(""); onDone && onDone();
  }
  return (
    <div>
      <textarea value={desc} onChange={e => setDesc(e.target.value)}
                placeholder="Documenta el dano preexistente..." rows={3} />
      <button onClick={reportar} disabled={!desc.trim()}>
        Documentar dano
      </button>
    </div>
  );
}
