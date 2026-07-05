package examenU2_020726;

public class Hijo_Botas extends Padre_Zapato {
    private double alturaCana;
    private String tipoCasquillo;
    private boolean esTermica;

    public Hijo_Botas(String tipo, String color, String calidad, double alturaCana, String tipoCasquillo, boolean esTermica) {
        super(tipo, color, calidad);
        this.alturaCana = alturaCana;
        this.tipoCasquillo = tipoCasquillo;
        this.esTermica = esTermica;
    }

    public double getAlturaCana() {
        return alturaCana;
    }

    public void setAlturaCana(double alturaCana) {
        this.alturaCana = alturaCana;
    }

    public String getTipoCasquillo() {
        return tipoCasquillo;
    }

    public void setTipoCasquillo(String tipoCasquillo) {
        this.tipoCasquillo = tipoCasquillo;
    }

    public boolean isEsTermica() {
        return esTermica;
    }

    public void setEsTermica(boolean esTermica) {
        this.esTermica = esTermica;
    }

    public void reforzarTobillo() {
        System.out.println("Reforzando tobillo y montando cana de " + alturaCana + " centimetros");
    }

    public void impermeabilizar() {
        System.out.println("Instalando casquillo de " + tipoCasquillo);
        if (esTermica) {
            System.out.println("Agregando forro termico interior");
        }
    }
}
