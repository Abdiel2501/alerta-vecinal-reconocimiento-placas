package examenU2_020726;

public class Hijo_Tacon extends Padre_Zapato {
    private double alturaTacon;
    private String tipoPunta;
    private boolean tienePlataforma;

    public Hijo_Tacon(String tipo, String color, String calidad, double alturaTacon, String tipoPunta, boolean tienePlataforma) {
        super(tipo, color, calidad);
        this.alturaTacon = alturaTacon;
        this.tipoPunta = tipoPunta;
        this.tienePlataforma = tienePlataforma;
    }

    public double getAlturaTacon() {
        return alturaTacon;
    }

    public void setAlturaTacon(double alturaTacon) {
        this.alturaTacon = alturaTacon;
    }

    public String getTipoPunta() {
        return tipoPunta;
    }

    public void setTipoPunta(String tipoPunta) {
        this.tipoPunta = tipoPunta;
    }

    public boolean isTienePlataforma() {
        return tienePlataforma;
    }

    public void setTienePlataforma(boolean tienePlataforma) {
        this.tienePlataforma = tienePlataforma;
    }

    public void fijarTacon() {
        System.out.println("Fijando tacon de " + alturaTacon + " centimetros con punta " + tipoPunta);
    }

    public void colocarPlantilla() {
        if (tienePlataforma) {
            System.out.println("Agregando plataforma frontal de soporte");
        }
        System.out.println("Colocando plantilla de confort");
    }
}
