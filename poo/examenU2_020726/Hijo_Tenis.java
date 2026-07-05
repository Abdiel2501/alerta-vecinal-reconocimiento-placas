package examenU2_020726;

public class Hijo_Tenis extends Padre_Zapato {
    private String tipoSuela;
    private String colorAgujetas;
    private boolean esImpermeable;

    public Hijo_Tenis(String tipo, String color, String calidad, String tipoSuela, String colorAgujetas, boolean esImpermeable) {
        super(tipo, color, calidad);
        this.tipoSuela = tipoSuela;
        this.colorAgujetas = colorAgujetas;
        this.esImpermeable = esImpermeable;
    }

    public String getTipoSuela() {
        return tipoSuela;
    }

    public void setTipoSuela(String tipoSuela) {
        this.tipoSuela = tipoSuela;
    }

    public String getColorAgujetas() {
        return colorAgujetas;
    }

    public void setColorAgujetas(String colorAgujetas) {
        this.colorAgujetas = colorAgujetas;
    }

    public boolean isEsImpermeable() {
        return esImpermeable;
    }

    public void setEsImpermeable(boolean esImpermeable) {
        this.esImpermeable = esImpermeable;
    }

    public void coserSuela() {
        System.out.println("Cosiendo suela tipo " + tipoSuela + " al tenis tradicional");
    }

    public void colocarAgujetas() {
        System.out.println("Colocando agujetas de color " + colorAgujetas);
        if (esImpermeable) {
            System.out.println("Aplicando spray protector contra agua");
        }
    }
}
