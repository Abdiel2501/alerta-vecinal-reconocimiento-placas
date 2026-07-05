package examenU2_020726;

public class Hijo_Sandalias extends Padre_Zapato {
    private int cantidadCorreas;
    private String tipoAjuste;
    private boolean esAntideslizante;

    public Hijo_Sandalias(String tipo, String color, String calidad, int cantidadCorreas, String tipoAjuste, boolean esAntideslizante) {
        super(tipo, color, calidad);
        this.cantidadCorreas = cantidadCorreas;
        this.tipoAjuste = tipoAjuste;
        this.esAntideslizante = esAntideslizante;
    }

    public int getCantidadCorreas() {
        return cantidadCorreas;
    }

    public void setCantidadCorreas(int cantidadCorreas) {
        this.cantidadCorreas = cantidadCorreas;
    }

    public String getTipoAjuste() {
        return tipoAjuste;
    }

    public void setTipoAjuste(String tipoAjuste) {
        this.tipoAjuste = tipoAjuste;
    }

    public boolean isEsAntideslizante() {
        return esAntideslizante;
    }

    public void setEsAntideslizante(boolean esAntideslizante) {
        this.esAntideslizante = esAntideslizante;
    }

    public void montarCorreas() {
        System.out.println("Montando " + cantidadCorreas + " correas con ajuste de tipo " + tipoAjuste);
    }

    public void asegurarHebilla() {
        if (esAntideslizante) {
            System.out.println("Colocando suela antideslizante de goma");
        }
        System.out.println("Asegurando hebillas y costuras de las correas");
    }
}
